# coding: utf-8
import logging
from urllib.parse import quote, urlparse

import requests
from flask import current_app

logger = logging.getLogger(__name__)

CLASSIC_ARTICLE_TIMEOUT = 5

_FOUND_MARKER = "citation_title"
_NOT_FOUND_MARKERS = (
    "documento não encontrado",
    "documento nao encontrado",
    "document not found",
    "documento no encontrado",
    "artigo não encontrado",
    "artigo nao encontrado",
    "article not found",
    "artículo no encontrado",
    "articulo no encontrado",
)


def _with_scheme(url):
    raw = (url or "").strip()
    if not raw:
        return ""
    if raw.startswith("//"):
        return "https:" + raw
    if "://" not in raw:
        return "https://" + raw
    return raw


def previous_website_base_url(raw_value=None):
    """Base absoluta do site clássico, ou None se a variável estiver vazia."""
    if raw_value is None:
        raw_value = current_app.config.get("PREVIOUS_WEBSITE_URI") or ""
    base = _with_scheme(raw_value).rstrip("/")
    return base or None


def classic_article_url(pid, raw_value=None):
    """URL do artigo no site clássico. None se não houver base ou PID."""
    if not pid:
        return None
    base = previous_website_base_url(raw_value)
    if not base:
        return None
    return "{}/scielo.php?script=sci_arttext&pid={}".format(
        base, quote(str(pid), safe="")
    )


def configured_search_host():
    """Hostname de URL_SEARCH, usado para voltar à página de resultados."""
    search_url = current_app.config.get("URL_SEARCH") or ""
    return (urlparse(_with_scheme(search_url)).hostname or "").lower() or None


def response_confirms_classic_article(status_code, text):
    """
    O site clássico pode responder 200 mesmo quando o documento não existe.
    A confirmação exige status 200, o marcador de artigo e a ausência das
    mensagens de documento inexistente.
    """
    if status_code != 200 or not text:
        return False
    lowered = text.lower()
    if any(marker in lowered for marker in _NOT_FOUND_MARKERS):
        return False
    return _FOUND_MARKER in lowered


def fetch_classic_article(url):
    """Um único GET, sem retentativa. Propaga requests.RequestException."""
    return requests.get(url, timeout=CLASSIC_ARTICLE_TIMEOUT, allow_redirects=True)
