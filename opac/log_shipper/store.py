# coding: utf-8
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone

SHIPMENT_COLUMNS = (
    "id",
    "relative_path",
    "object_key",
    "size",
    "md5",
    "sha256",
    "status",
    "attempts",
    "last_error",
    "updated_at",
    "uploaded_at",
)

RUN_COLUMNS = (
    "id",
    "started_at",
    "finished_at",
    "status",
    "error_message",
    "pending_count",
    "uploaded_count",
    "failed_count",
)

DDL = """
CREATE TABLE IF NOT EXISTS log_shipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relative_path TEXT NOT NULL UNIQUE,
    object_key TEXT NOT NULL,
    size INTEGER NOT NULL,
    md5 TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    updated_at TEXT NOT NULL,
    uploaded_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_log_shipment_status ON log_shipment (status);
CREATE TABLE IF NOT EXISTS log_shipper_run (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    error_message TEXT,
    pending_count INTEGER NOT NULL DEFAULT 0,
    uploaded_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0
);
"""


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Shipment:
    id: int
    relative_path: str
    object_key: str
    size: int
    md5: str
    sha256: str
    status: str
    attempts: int
    last_error: str
    updated_at: str
    uploaded_at: str


class Store:
    def __init__(self, database_path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(
            str(database_path), timeout=30, check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=30000")
        self.ensure_schema()

    def ensure_schema(self):
        with self._lock:
            self.conn.executescript(DDL)
            self.conn.commit()

    def _row_to_shipment(self, row):
        if row is None:
            return None
        return Shipment(
            id=row["id"],
            relative_path=row["relative_path"],
            object_key=row["object_key"],
            size=row["size"],
            md5=row["md5"],
            sha256=row["sha256"],
            status=row["status"],
            attempts=row["attempts"],
            last_error=row["last_error"],
            updated_at=row["updated_at"],
            uploaded_at=row["uploaded_at"],
        )

    def get_by_path(self, relative_path):
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM log_shipment WHERE relative_path = ?",
                (relative_path,),
            ).fetchone()
        return self._row_to_shipment(row)

    def upsert_pending(self, relative_path, object_key, size, md5, sha256):
        now = utc_now()
        existing = self.get_by_path(relative_path)
        attempts = 0
        last_error = None
        if existing and existing.sha256 == sha256:
            attempts = existing.attempts
            last_error = existing.last_error
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO log_shipment (
                    relative_path, object_key, size, md5, sha256, status,
                    attempts, last_error, updated_at, uploaded_at
                ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, NULL)
                ON CONFLICT(relative_path) DO UPDATE SET
                    object_key = excluded.object_key,
                    size = excluded.size,
                    md5 = excluded.md5,
                    sha256 = excluded.sha256,
                    status = 'pending',
                    attempts = excluded.attempts,
                    last_error = excluded.last_error,
                    updated_at = excluded.updated_at,
                    uploaded_at = NULL
                """,
                (
                    relative_path,
                    object_key,
                    size,
                    md5,
                    sha256,
                    attempts,
                    last_error,
                    now,
                ),
            )
            self.conn.commit()
        return self.get_by_path(relative_path)

    def mark_uploaded(self, relative_path):
        now = utc_now()
        with self._lock:
            self.conn.execute(
                """
                UPDATE log_shipment
                   SET status = 'uploaded',
                       last_error = NULL,
                       updated_at = ?,
                       uploaded_at = ?,
                       attempts = attempts + 1
                 WHERE relative_path = ?
                """,
                (now, now, relative_path),
            )
            self.conn.commit()

    def mark_failed(self, relative_path, error):
        now = utc_now()
        with self._lock:
            self.conn.execute(
                """
                UPDATE log_shipment
                   SET status = 'failed',
                       last_error = ?,
                       updated_at = ?,
                       attempts = attempts + 1
                 WHERE relative_path = ?
                """,
                (error, now, relative_path),
            )
            self.conn.commit()

    def mark_conflict(self, relative_path, error):
        now = utc_now()
        with self._lock:
            self.conn.execute(
                """
                UPDATE log_shipment
                   SET status = 'conflict',
                       last_error = ?,
                       updated_at = ?
                 WHERE relative_path = ?
                """,
                (error, now, relative_path),
            )
            self.conn.commit()

    def list_by_status(self, statuses):
        placeholders = ",".join("?" for _ in statuses)
        with self._lock:
            rows = self.conn.execute(
                "SELECT * FROM log_shipment WHERE status IN (%s) ORDER BY relative_path"
                % placeholders,
                tuple(statuses),
            ).fetchall()
        return [self._row_to_shipment(row) for row in rows]

    def list_uploaded(self):
        return self.list_by_status(("uploaded",))

    def count_status(self, status):
        with self._lock:
            row = self.conn.execute(
                "SELECT COUNT(*) AS n FROM log_shipment WHERE status = ?",
                (status,),
            ).fetchone()
        return row["n"]

    def counts(self):
        return {
            "pending": self.count_status("pending"),
            "uploaded": self.count_status("uploaded"),
            "failed": self.count_status("failed"),
            "conflict": self.count_status("conflict"),
        }

    def last_uploaded_at(self):
        with self._lock:
            row = self.conn.execute(
                "SELECT MAX(uploaded_at) AS uploaded_at FROM log_shipment"
            ).fetchone()
        return row["uploaded_at"] if row else None

    def delete_path(self, relative_path):
        with self._lock:
            self.conn.execute(
                "DELETE FROM log_shipment WHERE relative_path = ?",
                (relative_path,),
            )
            self.conn.commit()

    def start_run(self):
        now = utc_now()
        with self._lock:
            cursor = self.conn.execute(
                """
                INSERT INTO log_shipper_run (
                    started_at, status, pending_count, uploaded_count, failed_count
                ) VALUES (?, 'running', 0, 0, 0)
                """,
                (now,),
            )
            self.conn.commit()
            return cursor.lastrowid

    def finish_run(
        self, run_id, status, error_message, pending_count, uploaded_count, failed_count
    ):
        now = utc_now()
        with self._lock:
            self.conn.execute(
                """
                UPDATE log_shipper_run
                   SET finished_at = ?,
                       status = ?,
                       error_message = ?,
                       pending_count = ?,
                       uploaded_count = ?,
                       failed_count = ?
                 WHERE id = ?
                """,
                (
                    now,
                    status,
                    error_message,
                    pending_count,
                    uploaded_count,
                    failed_count,
                    run_id,
                ),
            )
            self.conn.commit()

    def latest_run(self):
        with self._lock:
            return self.conn.execute(
                "SELECT * FROM log_shipper_run ORDER BY id DESC LIMIT 1"
            ).fetchone()
