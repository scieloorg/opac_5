# coding: utf-8
"""Interface language resolution via ``ilang`` query param and Accept-Language."""

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from flask import current_app, g, request, url_for as flask_url_for

# Map primary language tags (and common variants) to LANGUAGES keys.
_PRIMARY_TO_CANONICAL = {
    "pt": "pt_BR",
    "en": "en",
    "es": "es",
}


def canonical_interface_lang(lang_code):
    """
    Map a free-form language code to a key in ``LANGUAGES``, or return None.
    Accepts values like ``pt_BR``, ``pt-BR``, ``pt``, ``en-US``, ``es_ES``.
    """
    if not lang_code:
        return None

    langs = current_app.config.get("LANGUAGES") or {}
    if lang_code in langs:
        return lang_code

    normalized = lang_code.replace("-", "_")
    if normalized in langs:
        return normalized

    # Case-insensitive key match (e.g. pt_br → pt_BR)
    lowered = {key.lower(): key for key in langs}
    if normalized.lower() in lowered:
        return lowered[normalized.lower()]

    primary = normalized.split("_")[0].lower()
    candidate = _PRIMARY_TO_CANONICAL.get(primary)
    if candidate and candidate in langs:
        return candidate
    return None


def match_accept_language():
    """
    Best-match browser Accept-Language against supported interface languages.
    Returns a canonical LANGUAGES key or None.
    """
    langs = current_app.config.get("LANGUAGES") or {}
    if not langs:
        return None

    offerings = []
    reverse = {}
    for key in langs:
        hyphen = key.replace("_", "-")
        offerings.append(hyphen)
        reverse[hyphen.lower()] = key
        reverse[key.lower()] = key
        primary = key.split("_")[0]
        primary_lower = primary.lower()
        if primary_lower not in reverse:
            offerings.append(primary)
            reverse[primary_lower] = key

    matched = request.accept_languages.best_match(offerings)
    if not matched:
        return None
    return reverse.get(matched.lower()) or canonical_interface_lang(matched)


def get_locale():
    """
    Resolve interface locale for the current request.

    Priority:
    1. ``ilang`` query string (if valid)
    2. Accept-Language autodiscovery
    3. BABEL_DEFAULT_LOCALE (pt_BR)
    """
    default = current_app.config.get("BABEL_DEFAULT_LOCALE", "pt_BR")

    from_ilang = canonical_interface_lang(request.args.get("ilang"))
    if from_ilang:
        return from_ilang

    from_headers = match_accept_language()
    if from_headers:
        return from_headers

    return default


def build_ilang_url(lang_code):
    """Current path + query string with ``ilang`` set to ``lang_code``."""
    args = request.args.to_dict(flat=True)
    args["ilang"] = lang_code
    return "%s?%s" % (request.path, urlencode(args))


def _is_static_endpoint(endpoint):
    if not endpoint:
        return False
    return endpoint == "static" or endpoint.endswith(".static")


def url_for_with_ilang(endpoint, **values):
    """
    Like ``flask.url_for``, but injects ``ilang`` from the current interface locale.

    Skips static endpoints. Does not overwrite an explicit ``ilang`` kwarg.
    """
    if not _is_static_endpoint(endpoint) and "ilang" not in values:
        values["ilang"] = getattr(g, "lang", None) or get_locale()
    return flask_url_for(endpoint, **values)


def inject_ilang_into_url(url, lang_code, fragment=None):
    """
    Return ``url`` with ``ilang`` replaced/added in the query string.
    Optionally set URL fragment (from legacy ``hash`` query on set_locale).
    """
    if not url:
        return None
    parsed = urlparse(url)
    qs = dict(parse_qsl(parsed.query, keep_blank_values=True))
    qs["ilang"] = lang_code
    new_fragment = fragment if fragment is not None else parsed.fragment
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(qs),
            new_fragment or "",
        )
    )
