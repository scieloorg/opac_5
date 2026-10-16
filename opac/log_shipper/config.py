# coding: utf-8
import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    pass


def _bool_env(env, name, default=False):
    raw = env.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _int_env(env, name, default):
    raw = env.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    return int(str(raw).strip())


def _csv_env(env, name, default):
    raw = env.get(name)
    if raw is None or str(raw).strip() == "":
        raw = default
    return tuple(part.strip() for part in str(raw).split(",") if part.strip())


def sqlite_database_path(env=None):
    env = os.environ if env is None else env
    uri = (env.get("OPAC_DATABASE_URI") or "").strip()
    prefix = "sqlite:///"
    if uri.startswith(prefix):
        raw = uri[len(prefix) :]
        return Path(raw)
    directory = env.get("OPAC_DATABASE_DIR", "/tmp")
    filename = env.get("OPAC_DATABASE_FILE", "opac.sqlite")
    return Path(directory) / filename


def _segment(name, value, allow_empty=False):
    value = (value or "").strip()
    if not value and allow_empty:
        return ""
    if not value or "/" in value or "\\" in value or value in (".", ".."):
        raise ConfigError("%s inválido: %r" % (name, value))
    return value


def normalize_endpoint(value):
    value = (value or "").strip().rstrip("/")
    if value.startswith("https://"):
        return value[len("https://") :], True
    if value.startswith("http://"):
        return value[len("http://") :], False
    return value, None


@dataclass
class Config:
    endpoint: str
    secure: bool
    public_base_url: str
    access_key: str
    secret_key: str
    bucket: str
    region: str
    collection: str
    origin: str
    producer: str
    source_dir: Path
    pending_dir: Path
    database_path: Path
    interval_seconds: int
    stable_seconds: int
    concurrency: int
    retry_max: int
    retry_backoff_seconds: float
    include_globs: tuple
    exclude_globs: tuple

    def object_key(self, relative_path):
        parts = [self.collection]
        if self.origin:
            parts.append(self.origin)
        parts.append(self.producer)
        parts.append(relative_path)
        return "/".join(parts)

    def browser_base(self):
        if self.public_base_url:
            return self.public_base_url.rstrip("/")
        if not self.endpoint:
            return ""
        scheme = "https" if self.secure else "http"
        return "%s://%s" % (scheme, self.endpoint)


def load_config(env=None, require_endpoint=False, require_source=False):
    env = os.environ if env is None else env
    endpoint, scheme_secure = normalize_endpoint(env.get("OPAC_LOG_SHIPPER_ENDPOINT"))
    if require_endpoint and not endpoint:
        raise ConfigError("OPAC_LOG_SHIPPER_ENDPOINT é obrigatório")
    if (
        "OPAC_LOG_SHIPPER_SECURE" in env
        and str(env.get("OPAC_LOG_SHIPPER_SECURE")).strip() != ""
    ):
        secure = _bool_env(env, "OPAC_LOG_SHIPPER_SECURE", False)
    elif scheme_secure is not None:
        secure = scheme_secure
    else:
        secure = False

    collection = (
        env.get("OPAC_LOG_SHIPPER_COLLECTION") or env.get("OPAC_COLLECTION") or "scl"
    )
    producer = env.get("OPAC_LOG_SHIPPER_PRODUCER", "")
    if require_endpoint:
        producer = _segment("OPAC_LOG_SHIPPER_PRODUCER", producer)
        collection = _segment("OPAC_LOG_SHIPPER_COLLECTION", collection)
    else:
        collection = (collection or "scl").strip()
        producer = (producer or "").strip()

    source_dir = Path(env.get("OPAC_LOG_SHIPPER_SOURCE_DIR", "")).expanduser()
    pending_dir = Path(env.get("OPAC_LOG_SHIPPER_PENDING_DIR", "")).expanduser()
    if require_source:
        if not str(source_dir):
            raise ConfigError("OPAC_LOG_SHIPPER_SOURCE_DIR é obrigatório")
        if not str(pending_dir):
            raise ConfigError("OPAC_LOG_SHIPPER_PENDING_DIR é obrigatório")

    backoff = env.get("OPAC_LOG_SHIPPER_RETRY_BACKOFF_SECONDS", "2")
    return Config(
        endpoint=endpoint,
        secure=secure,
        public_base_url=(env.get("OPAC_LOG_SHIPPER_PUBLIC_BASE_URL") or "")
        .strip()
        .rstrip("/"),
        access_key=(env.get("OPAC_LOG_SHIPPER_ACCESS_KEY") or "").strip(),
        secret_key=(env.get("OPAC_LOG_SHIPPER_SECRET_KEY") or "").strip(),
        bucket=(env.get("OPAC_LOG_SHIPPER_BUCKET") or "usage-logs").strip()
        or "usage-logs",
        region=(env.get("OPAC_LOG_SHIPPER_REGION") or "").strip(),
        collection=collection,
        origin=_segment(
            "OPAC_LOG_SHIPPER_ORIGIN",
            env.get("OPAC_LOG_SHIPPER_ORIGIN", ""),
            allow_empty=True,
        ),
        producer=producer,
        source_dir=source_dir,
        pending_dir=pending_dir,
        database_path=sqlite_database_path(env),
        interval_seconds=_int_env(env, "OPAC_LOG_SHIPPER_INTERVAL_SECONDS", 300),
        stable_seconds=_int_env(env, "OPAC_LOG_SHIPPER_STABLE_SECONDS", 60),
        concurrency=max(1, _int_env(env, "OPAC_LOG_SHIPPER_CONCURRENCY", 2)),
        retry_max=max(1, _int_env(env, "OPAC_LOG_SHIPPER_RETRY_MAX", 3)),
        retry_backoff_seconds=float(backoff),
        include_globs=_csv_env(env, "OPAC_LOG_SHIPPER_INCLUDE_GLOBS", "*.log,*.log.gz"),
        exclude_globs=_csv_env(
            env,
            "OPAC_LOG_SHIPPER_EXCLUDE_GLOBS",
            "opac-access.log,opac-error.log,*.tmp,*.temp,*.swp",
        ),
    )
