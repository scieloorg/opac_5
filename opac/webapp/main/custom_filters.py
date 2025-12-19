# coding: utf-8

from webapp import choices
from webapp.utils import utc_to_local


def trans_alpha2(value):
    """
    Traduz siglas de idioma de 2 caracteres para nome.
    """

    if value in choices.ISO3166_ALPHA2:
        return choices.ISO3166_ALPHA2[value]
    else:
        return value


def datetimefilter(value, format="%Y-%m-%d %H:%M"):
    return utc_to_local(value).strftime(format)


def get_absolute_url(url, base_url=""):
    """
    Returns an absolute URL. If the URL already starts with http:// or https://,
    returns it as-is. Otherwise, concatenates base_url with url.
    
    Args:
        url: The URL to process (may be relative or absolute)
        base_url: The base URL to prepend if url is relative (default: "")
    
    Returns:
        An absolute URL string
    """
    if not url:
        return ""
    
    # Check if URL is already absolute
    if url.startswith("http://") or url.startswith("https://"):
        return url
    
    # URL is relative, concatenate with base_url
    # Remove leading slash from url if present, as base_url should handle it
    url_cleaned = url.lstrip("/")
    return f"{base_url}{url_cleaned}"
