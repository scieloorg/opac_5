# coding: utf-8
import os

from markupsafe import Markup
from markupsafe import escape

from log_shipper.config import normalize_endpoint


def object_url(status, object_key, env=None):
    """Monta o link do objeto a partir do endereço configurado. Vazio se ainda não foi aceito."""
    if status != "uploaded" or not object_key:
        return ""
    env = os.environ if env is None else env
    base = (env.get("OPAC_LOG_SHIPPER_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if not base:
        endpoint, scheme_secure = normalize_endpoint(
            env.get("OPAC_LOG_SHIPPER_ENDPOINT")
        )
        if not endpoint:
            return ""
        if (
            "OPAC_LOG_SHIPPER_SECURE" in env
            and str(env.get("OPAC_LOG_SHIPPER_SECURE")).strip() != ""
        ):
            secure = str(env.get("OPAC_LOG_SHIPPER_SECURE")).strip().lower() in (
                "1",
                "true",
                "yes",
                "on",
            )
        elif scheme_secure is not None:
            secure = scheme_secure
        else:
            secure = False
        scheme = "https" if secure else "http"
        base = "%s://%s" % (scheme, endpoint)
    bucket = (
        env.get("OPAC_LOG_SHIPPER_BUCKET") or "usage-logs"
    ).strip() or "usage-logs"
    return "%s/%s/%s" % (base, bucket, str(object_key).lstrip("/"))


def minio_link_html(status, object_key, env=None):
    url = object_url(status, object_key, env=env)
    if not url:
        return object_key or ""
    return Markup("<a href='%s' target='_blank'>MinIO</a>" % escape(url))
