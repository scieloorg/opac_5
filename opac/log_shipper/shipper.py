# coding: utf-8
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from log_shipper.files import (
    discard_pending,
    file_digests,
    is_eligible,
    iter_source_files,
    resolve_send_path,
    stage_pending,
)
from log_shipper.storage import StorageError


class Shipper:
    def __init__(self, config, store, storage, clock=None, sleeper=None):
        self.config = config
        self.store = store
        self.storage = storage
        self.clock = clock or time.time
        self.sleeper = sleeper or time.sleep
        self._result_lock = threading.Lock()
        self.uploaded = []
        self.failed = []
        self.conflicts = []

    def run_once(self, ignore_stability=False):
        run_id = self.store.start_run()
        self._reset_cycle()
        try:
            self.prepare(ignore_stability=ignore_stability)
            self.upload_all()
            return self._finish(run_id)
        except Exception as exc:
            self.store.finish_run(
                run_id,
                "error",
                str(exc),
                self.store.count_status("pending"),
                len(self.uploaded),
                len(self.failed) + len(self.conflicts),
            )
            raise

    def send_file(self, raw_path):
        run_id = self.store.start_run()
        self._reset_cycle()
        try:
            path, relative = resolve_send_path(self.config, raw_path)
            self.prepare(
                ignore_stability=True, only_relative=relative, known=(path, relative)
            )
            self.upload_all(only_relative=relative)
            return self._finish(run_id)
        except Exception as exc:
            self.store.finish_run(
                run_id,
                "error",
                str(exc),
                self.store.count_status("pending"),
                len(self.uploaded),
                len(self.failed) + len(self.conflicts),
            )
            raise

    def check(self):
        run_id = self.store.start_run()
        ok = []
        missing = []
        mismatch = []
        try:
            for row in self.store.list_uploaded():
                stat = self.storage.stat(row.object_key)
                if stat is None:
                    missing.append(row)
                elif stat.size == row.size and stat.etag == row.md5:
                    ok.append(row)
                else:
                    mismatch.append(row)
        except StorageError as exc:
            self.store.finish_run(run_id, "error", str(exc), 0, 0, 0)
            raise
        lines = [
            "check: %s conferidos, %s ausentes, %s divergentes"
            % (len(ok), len(missing), len(mismatch))
        ]
        for row in missing:
            lines.append("ausente: %s" % row.object_key)
        for row in mismatch:
            lines.append("divergente: %s" % row.object_key)
        message = "\n".join(lines)
        status = "success" if not missing and not mismatch else "error"
        self.store.finish_run(
            run_id,
            status,
            message,
            0,
            len(ok),
            len(missing) + len(mismatch),
        )
        return {"ok": ok, "missing": missing, "mismatch": mismatch, "status": status}

    def prepare(self, ignore_stability=False, only_relative=None, known=None):
        now = self.clock()
        if known is not None:
            path, relative = known
            self._stage(path, relative)
            return
        source = Path(self.config.source_dir)
        if source.is_dir():
            for path, relative in iter_source_files(source):
                if only_relative is not None and relative != only_relative:
                    continue
                mtime = path.stat().st_mtime
                if not is_eligible(relative, mtime, now, self.config, ignore_stability):
                    continue
                self._stage(path, relative)
        elif only_relative is None and not source.exists():
            raise FileNotFoundError("diretório de origem inexistente: %s" % source)

    def _stage(self, path, relative):
        pending = stage_pending(path, self.config.pending_dir, relative)
        size, md5, sha256 = file_digests(pending)
        key = self.config.object_key(relative)
        row = self.store.get_by_path(relative)
        if (
            row
            and row.object_key == key
            and row.sha256 == sha256
            and row.status in ("uploaded", "conflict")
        ):
            return
        self.store.upsert_pending(relative, key, size, md5, sha256)

    def upload_all(self, only_relative=None):
        rows = [
            row
            for row in self.store.list_by_status(("pending", "failed"))
            if only_relative is None or row.relative_path == only_relative
        ]
        if not rows:
            return
        workers = min(self.config.concurrency, len(rows))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(self._upload_with_retry, row) for row in rows]
            for future in as_completed(futures):
                future.result()

    def _upload_with_retry(self, row):
        delay = self.config.retry_backoff_seconds
        last_error = None
        for attempt in range(1, self.config.retry_max + 1):
            try:
                outcome = self._upload_once(row)
            except StorageError as exc:
                last_error = str(exc)
                self.store.mark_failed(row.relative_path, last_error)
                if attempt < self.config.retry_max:
                    self.sleeper(delay)
                    delay *= 2
                continue
            with self._result_lock:
                if outcome == "uploaded":
                    self.uploaded.append(row.relative_path)
                elif outcome == "conflict":
                    self.conflicts.append(row.relative_path)
            return outcome
        with self._result_lock:
            self.failed.append(row.relative_path)
        return "failed"

    def _upload_once(self, row):
        pending = Path(self.config.pending_dir) / row.relative_path
        source = Path(self.config.source_dir) / row.relative_path
        if not pending.is_file() and source.is_file():
            pending = stage_pending(source, self.config.pending_dir, row.relative_path)
        if not pending.is_file():
            raise StorageError("arquivo pendente ausente")
        fresh = self.store.get_by_path(row.relative_path)
        stat = self.storage.stat(fresh.object_key)
        if stat is None:
            self.storage.put(fresh.object_key, str(pending), fresh.size)
            self.store.mark_uploaded(fresh.relative_path)
            discard_pending(self.config.pending_dir, fresh.relative_path)
            return "uploaded"
        if stat.size == fresh.size and stat.etag == fresh.md5:
            self.store.mark_uploaded(fresh.relative_path)
            discard_pending(self.config.pending_dir, fresh.relative_path)
            return "uploaded"
        self.store.mark_conflict(
            fresh.relative_path,
            "objeto já existe com conteúdo diferente",
        )
        return "conflict"

    def _reset_cycle(self):
        self.uploaded = []
        self.failed = []
        self.conflicts = []

    def _finish(self, run_id):
        messages = []
        for relative in self.failed:
            row = self.store.get_by_path(relative)
            messages.append("%s: %s" % (relative, row.last_error if row else "falha"))
        for relative in self.conflicts:
            messages.append("%s: conflito de conteúdo" % relative)
        status = "error" if messages else "success"
        self.store.finish_run(
            run_id,
            status,
            "\n".join(messages) or None,
            self.store.count_status("pending") + self.store.count_status("failed"),
            len(self.uploaded),
            len(self.failed) + len(self.conflicts),
        )
        return {
            "status": status,
            "uploaded": list(self.uploaded),
            "failed": list(self.failed),
            "conflicts": list(self.conflicts),
        }
