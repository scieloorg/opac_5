# coding: utf-8
from dataclasses import dataclass


class StorageError(Exception):
    pass


@dataclass
class ObjectStat:
    size: int
    etag: str


def normalize_etag(etag):
    return (etag or "").strip().strip('"').lower()


class MinioStorage:
    def __init__(self, config):
        self.config = config
        self._client = None

    def _minio(self):
        if self._client is None:
            from minio import Minio

            self._client = Minio(
                self.config.endpoint,
                access_key=self.config.access_key,
                secret_key=self.config.secret_key,
                secure=self.config.secure,
                region=self.config.region or None,
            )
        return self._client

    def stat(self, key):
        from minio.error import S3Error

        try:
            obj = self._minio().stat_object(self.config.bucket, key)
        except S3Error as exc:
            if exc.code in ("NoSuchKey", "NoSuchObject"):
                return None
            raise StorageError(str(exc)) from exc
        except Exception as exc:
            raise StorageError(str(exc)) from exc
        return ObjectStat(size=obj.size, etag=normalize_etag(obj.etag))

    def put(self, key, file_path, size):
        part_size = max(int(size), 5 * 1024 * 1024)
        try:
            with open(file_path, "rb") as handle:
                result = self._minio().put_object(
                    self.config.bucket,
                    key,
                    handle,
                    length=size,
                    part_size=part_size,
                    content_type="application/octet-stream",
                )
        except Exception as exc:
            raise StorageError(str(exc)) from exc
        return normalize_etag(result.etag)
