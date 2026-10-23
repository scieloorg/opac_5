# coding: utf-8
import gzip
import hashlib
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from log_shipper.cli import main
from log_shipper.config import ConfigError, load_config
from log_shipper.files import RejectedPath, stage_pending
from log_shipper.links import object_url
from log_shipper.shipper import Shipper
from log_shipper.storage import MinioStorage, ObjectStat, StorageError
from log_shipper.store import RUN_COLUMNS, SHIPMENT_COLUMNS, Store


LOG_LINE = (
    b"45.65.189.47 - [06/Oct/2024:00:00:16 -0300] "
    b'"GET /scielo.php?lng=es&pid=S0213-91112023000100500&script=sci_abstract HTTP/1.1" '
    b'200 166 "-" "Mozilla/5.0"\n'
)


class MemoryStorage:
    def __init__(self):
        self.objects = {}
        self.puts = []
        self.down = False
        self.fail_remaining = 0
        self.ensure_calls = 0

    def ensure_bucket(self):
        self.ensure_calls += 1

    def _touch(self):
        if self.down:
            raise StorageError("minio inacessível")
        if self.fail_remaining:
            self.fail_remaining -= 1
            raise StorageError("falha temporária")

    def stat(self, key):
        self._touch()
        if key not in self.objects:
            return None
        data = self.objects[key]
        return ObjectStat(size=len(data), etag=hashlib.md5(data).hexdigest())

    def put(self, key, file_path, size):
        self._touch()
        data = Path(file_path).read_bytes()
        self.puts.append(key)
        self.objects[key] = data
        return hashlib.md5(data).hexdigest()


class LogShipperTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.logs = self.root / "logs"
        self.pending = self.root / "pending"
        self.logs.mkdir()
        self.pending.mkdir()
        self.storage = MemoryStorage()
        self.config = self._config()
        self.store = Store(self.config.database_path)
        self.shipper = self._shipper()

    def tearDown(self):
        self.tmp.cleanup()

    def _config(self, **overrides):
        env = {
            "OPAC_LOG_SHIPPER_ENDPOINT": "minio.example:9000",
            "OPAC_LOG_SHIPPER_SECURE": "true",
            "OPAC_LOG_SHIPPER_ACCESS_KEY": "key",
            "OPAC_LOG_SHIPPER_SECRET_KEY": "secret",
            "OPAC_LOG_SHIPPER_BUCKET": "usage-logs",
            "OPAC_LOG_SHIPPER_COLLECTION": "scl",
            "OPAC_LOG_SHIPPER_PRODUCER": "server-01",
            "OPAC_LOG_SHIPPER_SOURCE_DIR": str(self.logs),
            "OPAC_LOG_SHIPPER_PENDING_DIR": str(self.pending),
            "OPAC_DATABASE_DIR": str(self.root),
            "OPAC_DATABASE_FILE": "opac.sqlite",
            "OPAC_LOG_SHIPPER_STABLE_SECONDS": "60",
            "OPAC_LOG_SHIPPER_RETRY_MAX": "2",
            "OPAC_LOG_SHIPPER_RETRY_BACKOFF_SECONDS": "0",
            "OPAC_LOG_SHIPPER_CONCURRENCY": "2",
        }
        env.update(overrides)
        return load_config(env, require_endpoint=True, require_source=True)

    def _shipper(self, config=None):
        config = config or self.config
        return Shipper(config, self.store, self.storage, sleeper=lambda _delay: None)

    def _write(self, relative, content, age=3600):
        path = self.logs / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            content = content.encode("utf-8")
        path.write_bytes(content)
        stamp = time.time() - age
        os.utime(path, (stamp, stamp))
        return path

    def test_missing_endpoint_is_rejected(self):
        with self.assertRaises(ConfigError):
            load_config({}, require_endpoint=True, require_source=True)

    def test_blank_source_dirs_are_rejected(self):
        with self.assertRaises(ConfigError):
            self._config(
                OPAC_LOG_SHIPPER_SOURCE_DIR="  ",
                OPAC_LOG_SHIPPER_PENDING_DIR="",
            )
        with self.assertRaises(ConfigError):
            self._config(OPAC_LOG_SHIPPER_PENDING_DIR="")

    def test_same_source_and_pending_dir_are_rejected(self):
        with self.assertRaises(ConfigError):
            self._config(
                OPAC_LOG_SHIPPER_SOURCE_DIR=str(self.logs),
                OPAC_LOG_SHIPPER_PENDING_DIR=str(self.logs) + "/",
            )

    def test_create_bucket_defaults_to_false(self):
        self.assertFalse(self.config.create_bucket)
        enabled = self._config(OPAC_LOG_SHIPPER_CREATE_BUCKET="true")
        self.assertTrue(enabled.create_bucket)

    def test_cli_refuses_to_start_without_endpoint(self):
        previous = os.environ.pop("OPAC_LOG_SHIPPER_ENDPOINT", None)
        try:
            self.assertEqual(main(["once"]), 2)
        finally:
            if previous is not None:
                os.environ["OPAC_LOG_SHIPPER_ENDPOINT"] = previous

    def test_key_preserves_year_month_and_name(self):
        payload = gzip.compress(LOG_LINE)
        relative = "2026/Apr/scielo-2026-04-22.log.gz"
        self._write(relative, payload)
        result = self.shipper.run_once()
        key = "scl/server-01/2026/Apr/scielo-2026-04-22.log.gz"
        self.assertEqual(result["uploaded"], [relative])
        self.assertEqual(self.storage.puts, [key])
        self.assertNotIn("/22/", key)
        self.assertEqual(self.storage.objects[key], payload)
        self.assertEqual(gzip.decompress(self.storage.objects[key]), LOG_LINE)
        self.assertTrue((self.logs / relative).is_file())
        self.assertFalse((self.pending / relative).exists())

    def test_optional_origin_segment(self):
        self.config = self._config(
            OPAC_LOG_SHIPPER_COLLECTION="wid",
            OPAC_LOG_SHIPPER_ORIGIN="opac",
        )
        self.shipper = self._shipper()
        relative = "2026/May/arquivo-2026-05-20.log.gz"
        self._write(relative, gzip.compress(LOG_LINE))
        self.shipper.run_once()
        self.assertEqual(
            self.storage.puts,
            ["wid/opac/server-01/2026/May/arquivo-2026-05-20.log.gz"],
        )

    def test_open_and_temporary_files_are_skipped(self):
        self._write("opac-access.log", LOG_LINE)
        self._write("opac-error.log", b"erro\n")
        self._write("parcial.tmp", LOG_LINE)
        self._write("2026/Apr/fechado.log.gz", gzip.compress(LOG_LINE))
        self.shipper.run_once()
        self.assertEqual(len(self.storage.puts), 1)
        self.assertTrue(self.storage.puts[0].endswith("2026/Apr/fechado.log.gz"))

    def test_recent_file_is_not_sent_by_scan(self):
        self._write("2026/Apr/novo.log.gz", gzip.compress(LOG_LINE), age=1)
        self.shipper.run_once()
        self.assertEqual(self.storage.puts, [])

    def test_repeat_and_restart_do_not_duplicate_objects(self):
        relative = "2026/Apr/scielo-2026-04-22.log.gz"
        self._write(relative, gzip.compress(LOG_LINE))
        self.shipper.run_once()
        self.shipper.run_once()
        self.assertEqual(len(self.storage.puts), 1)
        self.store.delete_path(relative)
        self.shipper.run_once()
        self.assertEqual(len(self.storage.puts), 1)
        row = self.store.get_by_path(relative)
        self.assertEqual(row.status, "uploaded")

    def test_second_scan_does_not_recreate_pending(self):
        relative = "2026/Apr/scielo-2026-04-22.log.gz"
        self._write(relative, gzip.compress(LOG_LINE))
        self.shipper.run_once()
        self.assertFalse((self.pending / relative).exists())
        leftover = self.pending / relative
        leftover.parent.mkdir(parents=True, exist_ok=True)
        leftover.write_bytes(b"orfao")
        self.shipper.run_once()
        self.assertFalse(leftover.exists())
        self.assertEqual(len(self.storage.puts), 1)
        self.assertEqual(self.store.get_by_path(relative).status, "uploaded")
        self.assertGreaterEqual(self.storage.ensure_calls, 2)

    def test_network_failure_keeps_pending_and_records_error(self):
        relative = "2026/Apr/scielo-2026-04-22.log.gz"
        source = self._write(relative, gzip.compress(LOG_LINE))
        self.storage.down = True
        result = self.shipper.run_once()
        self.assertEqual(result["status"], "error")
        self.assertEqual(self.storage.puts, [])
        self.assertTrue(source.is_file())
        self.assertTrue((self.pending / relative).is_file())
        row = self.store.get_by_path(relative)
        self.assertEqual(row.status, "failed")
        self.assertIn("minio", row.last_error)
        run = self.store.latest_run()
        self.assertEqual(run["status"], "error")
        self.assertIn(relative, run["error_message"])

    def test_retry_then_success(self):
        relative = "2026/Apr/scielo-2026-04-22.log.gz"
        self._write(relative, gzip.compress(LOG_LINE))
        self.storage.fail_remaining = 1
        result = self.shipper.run_once()
        self.assertEqual(result["uploaded"], [relative])
        self.assertEqual(self.store.get_by_path(relative).status, "uploaded")

    def test_pending_survives_source_removal(self):
        relative = "2026/Apr/scielo-2026-04-22.log.gz"
        payload = gzip.compress(LOG_LINE)
        source = self._write(relative, payload)
        self.storage.down = True
        self.shipper.run_once()
        source.unlink()
        self.storage.down = False
        self.shipper.run_once()
        key = "scl/server-01/" + relative
        self.assertEqual(self.storage.objects[key], payload)
        self.assertFalse(source.exists())
        self.assertFalse((self.pending / relative).exists())
        self.assertEqual(self.store.get_by_path(relative).status, "uploaded")

    def test_conflict_does_not_overwrite(self):
        relative = "2026/Apr/scielo-2026-04-22.log.gz"
        payload = gzip.compress(LOG_LINE)
        source = self._write(relative, payload)
        key = "scl/server-01/" + relative
        self.storage.objects[key] = b"conteudo-diferente"
        result = self.shipper.run_once()
        self.assertEqual(self.storage.puts, [])
        self.assertEqual(self.storage.objects[key], b"conteudo-diferente")
        self.assertEqual(result["conflicts"], [relative])
        self.assertEqual(self.store.get_by_path(relative).status, "conflict")
        self.assertTrue(source.is_file())
        self.assertTrue((self.pending / relative).is_file())

    def test_scan_keeps_conflict_and_send_rechecks_minio(self):
        relative = "2026/Apr/scielo-2026-04-22.log.gz"
        payload = gzip.compress(LOG_LINE)
        self._write(relative, payload)
        key = "scl/server-01/" + relative
        self.storage.objects[key] = b"conteudo-diferente"
        self.shipper.run_once()
        self.assertEqual(self.store.get_by_path(relative).status, "conflict")

        self.storage.down = True
        result = self.shipper.run_once()
        self.storage.down = False
        self.assertEqual(result["status"], "success")
        self.assertEqual(self.storage.puts, [])
        self.assertEqual(self.store.get_by_path(relative).status, "conflict")
        self.assertEqual(self.storage.objects[key], b"conteudo-diferente")

        result = self.shipper.send_file(str(self.logs / relative))
        self.assertEqual(result["conflicts"], [relative])
        self.assertEqual(self.storage.puts, [])
        self.assertEqual(self.storage.objects[key], b"conteudo-diferente")
        self.assertEqual(self.store.get_by_path(relative).status, "conflict")

        del self.storage.objects[key]
        result = self.shipper.send_file(str(self.logs / relative))
        self.assertEqual(result["uploaded"], [relative])
        self.assertEqual(self.storage.objects[key], payload)
        self.assertEqual(self.store.get_by_path(relative).status, "uploaded")
        self.assertFalse((self.pending / relative).exists())

    def test_stage_pending_hardlink_or_copy_leaves_source(self):
        source = self._write("2026/Apr/arquivo.log.gz", gzip.compress(LOG_LINE))
        dest = stage_pending(source, self.pending, "2026/Apr/arquivo.log.gz")
        self.assertEqual(source.stat().st_ino, dest.stat().st_ino)
        before = source.read_bytes()
        with patch("log_shipper.files.os.link", side_effect=OSError("cross-device")):
            other = self._write("2026/May/outro.log.gz", b"abc")
            copied = stage_pending(other, self.pending, "2026/May/outro.log.gz")
        self.assertNotEqual(other.stat().st_ino, copied.stat().st_ino)
        self.assertEqual(other.read_bytes(), b"abc")
        self.assertEqual(source.read_bytes(), before)

    def test_send_one_file_ignores_mtime_window(self):
        relative = "2026/Apr/recente.log.gz"
        payload = gzip.compress(LOG_LINE)
        self._write(relative, payload, age=1)
        self._write("2026/Apr/outro.log.gz", gzip.compress(b"outro\n"))
        result = self.shipper.send_file(str(self.logs / relative))
        self.assertEqual(result["uploaded"], [relative])
        self.assertEqual(self.storage.puts, ["scl/server-01/" + relative])

    def test_send_rejects_path_outside_source_and_open_log(self):
        with self.assertRaises(RejectedPath):
            self.shipper.send_file("/etc/passwd")
        self._write("opac-access.log", LOG_LINE, age=1)
        with self.assertRaises(RejectedPath):
            self.shipper.send_file("opac-access.log")
        self.assertEqual(self.storage.puts, [])

    def test_check_ok_missing_mismatch_and_outage(self):
        relative = "2026/Apr/scielo-2026-04-22.log.gz"
        payload = gzip.compress(LOG_LINE)
        self._write(relative, payload)
        self.shipper.run_once()
        puts = list(self.storage.puts)
        report = self.shipper.check()
        self.assertEqual(len(report["ok"]), 1)
        self.assertEqual(report["missing"], [])
        self.assertEqual(report["mismatch"], [])
        self.assertEqual(self.storage.puts, puts)
        self.assertEqual(self.store.get_by_path(relative).status, "uploaded")

        key = "scl/server-01/" + relative
        del self.storage.objects[key]
        report = self.shipper.check()
        self.assertEqual(len(report["missing"]), 1)
        self.assertEqual(self.store.get_by_path(relative).status, "uploaded")
        self.assertEqual(self.storage.puts, puts)

        self.storage.objects[key] = b"outro"
        report = self.shipper.check()
        self.assertEqual(len(report["mismatch"]), 1)
        self.assertEqual(self.store.get_by_path(relative).status, "uploaded")
        self.assertEqual(self.storage.puts, puts)

        self.storage.objects[key] = payload
        self.storage.down = True
        with self.assertRaises(StorageError):
            self.shipper.check()
        self.assertEqual(self.store.get_by_path(relative).status, "uploaded")
        run = self.store.latest_run()
        self.assertEqual(run["status"], "error")
        self.assertNotIn("ausente", run["error_message"])

    def test_schema_matches_sqlalchemy_models(self):
        from webapp.models import LogShipment, LogShipperRun

        shipment_cols = {column.name for column in LogShipment.__table__.columns}
        run_cols = {column.name for column in LogShipperRun.__table__.columns}
        self.assertEqual(shipment_cols, set(SHIPMENT_COLUMNS))
        self.assertEqual(run_cols, set(RUN_COLUMNS))
        info = self.store.conn.execute("PRAGMA table_info(log_shipment)").fetchall()
        self.assertEqual({row[1] for row in info}, shipment_cols)
        info = self.store.conn.execute("PRAGMA table_info(log_shipper_run)").fetchall()
        self.assertEqual({row[1] for row in info}, run_cols)

    def test_admin_link_uses_configured_address_only_after_upload(self):
        webapp_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "webapp")
        )
        if webapp_path not in sys.path:
            sys.path.insert(0, webapp_path)
        from webapp.admin.log_shipper_views import (
            LogShipmentAdminView,
            LogShipperRunAdminView,
        )

        self.assertFalse(LogShipmentAdminView.can_create)
        self.assertFalse(LogShipmentAdminView.can_edit)
        self.assertFalse(LogShipmentAdminView.can_delete)
        self.assertIn("status", LogShipmentAdminView.column_filters)
        self.assertIn("status", LogShipperRunAdminView.column_filters)

        env = {
            "OPAC_LOG_SHIPPER_ENDPOINT": "logs.example:9000",
            "OPAC_LOG_SHIPPER_SECURE": "true",
            "OPAC_LOG_SHIPPER_BUCKET": "usage-logs",
            "OPAC_LOG_SHIPPER_PUBLIC_BASE_URL": "",
        }
        previous = {key: os.environ.get(key) for key in env}
        os.environ.update(env)
        try:
            pending = SimpleNamespace(
                status="pending", object_key="scl/server-01/a.log.gz"
            )
            shown = LogShipmentAdminView._minio_formatter(
                None, None, pending, "object_key"
            )
            self.assertEqual(shown, "scl/server-01/a.log.gz")
            self.assertNotIn("href", str(shown))

            uploaded = SimpleNamespace(
                status="uploaded", object_key="scl/server-01/a.log.gz"
            )
            html = str(
                LogShipmentAdminView._minio_formatter(
                    None, None, uploaded, "object_key"
                )
            )
            self.assertIn(
                "https://logs.example:9000/usage-logs/scl/server-01/a.log.gz",
                html,
            )
            self.assertIn("target='_blank'", html)

            os.environ["OPAC_LOG_SHIPPER_PUBLIC_BASE_URL"] = "https://logs.scielo.org"
            self.assertEqual(
                object_url("uploaded", "scl/server-01/a.log.gz"),
                "https://logs.scielo.org/usage-logs/scl/server-01/a.log.gz",
            )
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_ensure_bucket_creates_missing_bucket_only_when_enabled(self):
        from minio.error import S3Error

        disabled = MinioStorage(self.config)
        with patch.object(disabled, "_minio") as minio:
            disabled.ensure_bucket()
        minio.assert_not_called()

        enabled = MinioStorage(
            self._config(
                OPAC_LOG_SHIPPER_CREATE_BUCKET="true",
                OPAC_LOG_SHIPPER_REGION="us-east-1",
            )
        )
        client = MagicMock()
        client.bucket_exists.return_value = False
        with patch.object(enabled, "_minio", return_value=client):
            enabled.ensure_bucket()
        client.make_bucket.assert_called_once_with("usage-logs", location="us-east-1")

        client.bucket_exists.return_value = True
        client.make_bucket.reset_mock()
        with patch.object(enabled, "_minio", return_value=client):
            enabled.ensure_bucket()
        client.make_bucket.assert_not_called()

        client.bucket_exists.return_value = False
        client.make_bucket.side_effect = S3Error(
            "BucketAlreadyOwnedByYou",
            "owned",
            "usage-logs",
            "req",
            "host",
            None,
        )
        with patch.object(enabled, "_minio", return_value=client):
            enabled.ensure_bucket()

        client.make_bucket.side_effect = S3Error(
            "AccessDenied",
            "denied",
            "usage-logs",
            "req",
            "host",
            None,
        )
        with patch.object(enabled, "_minio", return_value=client):
            with self.assertRaises(StorageError):
                enabled.ensure_bucket()
