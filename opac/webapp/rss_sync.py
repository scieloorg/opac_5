# coding: utf-8

import logging
import re
from datetime import datetime
from uuid import uuid4

import feedparser
import requests
import webapp
from flask import current_app, has_app_context
from mongoengine.errors import ValidationError
from opac_schema.v1 import models
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

RSS_SYNC_USER_AGENT = "SciELO-OPAC-RSS-Sync/1.0"
_IMG_SRC_RE = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.IGNORECASE)


def extract_image_url(entry):
    """Return the best image URL from a feedparser entry, or None."""
    media = entry.get("media_content") or []
    if media:
        last = media[-1] if isinstance(media[-1], dict) else {}
        url = last.get("url")
        if url:
            return url

    for link in entry.get("links") or []:
        if not isinstance(link, dict):
            continue
        rel = link.get("rel")
        link_type = link.get("type") or ""
        if rel == "enclosure" and link_type.startswith("image"):
            href = link.get("href")
            if href:
                return href

    html_chunks = []
    summary = entry.get("summary")
    if summary:
        html_chunks.append(summary)
    for item in entry.get("content") or []:
        if isinstance(item, dict) and item.get("value"):
            html_chunks.append(item["value"])
        elif isinstance(item, str):
            html_chunks.append(item)
    for chunk in html_chunks:
        match = _IMG_SRC_RE.search(chunk)
        if match:
            return match.group(1)
    return None


def parse_publication_date(entry):
    try:
        return datetime.strptime(entry["published"][5:25], "%d %b %Y %X")
    except (ValueError, KeyError, TypeError, IndexError):
        return datetime.now()


def build_news(entry, language):
    """Map a RSS entry to a News document, upserting by url."""
    url = entry.get("id")

    try:
        news = models.News.objects.get(url=url)
    except models.News.DoesNotExist:
        news = models.News()
        news._id = uuid4().hex

    news.url = url
    news.title = entry.get("title")
    news.description = entry.get("summary")
    news.image_url = extract_image_url(entry)
    news.publication_date = parse_publication_date(entry)
    news.language = language
    return news


def build_press_release(entry, journal, language):
    """Map a RSS entry to a PressRelease document, upserting by url."""
    url = entry.get("id")

    try:
        press_release = models.PressRelease.objects.get(url=url)
    except models.PressRelease.DoesNotExist:
        press_release = models.PressRelease()
        press_release._id = uuid4().hex

    press_release.url = url
    press_release.title = entry.get("title")
    press_release.journal = journal
    press_release.language = language
    press_release.content = entry.get("summary")
    press_release.image_url = extract_image_url(entry)
    press_release.publication_date = parse_publication_date(entry)
    return press_release


@retry(
    wait=wait_exponential(),
    stop=stop_after_attempt(4),
    retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
)
def fetch_rss(url):
    return requests.get(
        url,
        timeout=10,
        headers={"User-Agent": RSS_SYNC_USER_AGENT},
    )


def _http_error(response, feed_url):
    if response.status_code >= 400:
        logger.error(
            "Could not fetch feed from '%s'. HTTP status %s.",
            feed_url,
            response.status_code,
        )
        return True
    return False


def try_fetch_and_register_news_feed(rss_news_feeds):
    """Fetch news RSS feeds and upsert News documents.

    Returns a list of News documents that were created in this run
    (updates of existing URLs are not included).
    """
    created_news = []
    for language, feed in rss_news_feeds.items():
        feed_url = feed["url"]
        try:
            response = fetch_rss(feed_url)
        except RetryError:
            logger.error("Could not fetch feed from '%s'.", feed_url)
            continue

        if _http_error(response, feed_url):
            continue

        content = feedparser.parse(response.content)
        if content.bozo == 1:
            logger.error(
                "Could not parse feed content from '%s'. During processing this error '%s' was thrown.",
                feed_url,
                content.bozo_exception,
            )

        for entry in content.get("entries", []):
            url = entry.get("id")
            existed = bool(url) and models.News.objects(url=url).first() is not None
            try:
                news = build_news(entry, language)
                news.save()
            except ValidationError as exc:
                logger.error(
                    "Could not save entry '%s', Please verify '%s'", entry, exc
                )
            else:
                logger.info("News '%s', saved successfully.", news.title)
                if not existed:
                    created_news.append(news)
    return created_news


def send_sync_notification(created_news=None, created_press_releases=None):
    """Email recipients with newly imported news and/or press-releases."""
    from flask import render_template
    from webapp.utils import send_email

    created_news = created_news or []
    created_press_releases = created_press_releases or []
    if not created_news and not created_press_releases:
        logger.info("Nenhum item novo para notificar por email.")
        return

    if not current_app.config.get("RSS_SYNC_NOTIFICATION_ENABLED", True):
        logger.info(
            "Notificação de sync RSS desativada. Verifique RSS_SYNC_NOTIFICATION_ENABLED."
        )
        return

    recipients = current_app.config.get("RSS_SYNC_NOTIFICATION_RECIPIENTS") or []
    if not recipients:
        logger.warning(
            "Nenhum destinatário configurado em RSS_SYNC_NOTIFICATION_RECIPIENTS."
        )
        return

    report_date = datetime.today().strftime("%Y-%m-%d")
    collection_acronym = current_app.config.get("OPAC_COLLECTION", "")
    parts = []
    if created_news:
        parts.append("%s notícia(s) nova(s)" % len(created_news))
    if created_press_releases:
        parts.append("%s press-release(s) novo(s)" % len(created_press_releases))
    subject = "[%s] - %s importado(s) (%s)" % (
        collection_acronym,
        " e ".join(parts),
        report_date,
    )
    html = render_template(
        "admin/email/rss_news_sync_report.html",
        news_items=created_news,
        press_releases=created_press_releases,
        report_date=report_date,
    )
    sent, error = send_email(recipients, subject, html)
    if sent:
        logger.info(
            "Email de sync RSS enviado para %s (%s notícia(s), %s press-release(s)).",
            recipients,
            len(created_news),
            len(created_press_releases),
        )
    else:
        logger.error("Falha ao enviar email de sync RSS: %s", error)


def try_fetch_and_register_press_release_feed(rss_press_release):
    """Fetch press-release RSS feeds per public/current journal and upsert.

    Returns a list of PressRelease documents created in this run
    (updates of existing URLs are not included).
    """
    created_press_releases = []
    journals = models.Journal.objects.filter(is_public=True, current_status="current")
    for journal in journals:
        for lang, feed in rss_press_release.items():
            feed_url_by_lang = feed["url"].format(lang, journal.acronym)
            try:
                response = fetch_rss(feed_url_by_lang)
            except RetryError:
                logger.error("Could not fetch feed from '%s'.", feed_url_by_lang)
                continue

            if _http_error(response, feed_url_by_lang):
                continue

            content = feedparser.parse(response.content)
            if content.bozo == 1:
                logger.error(
                    "Could not parse feed content from '%s'. During processing this error '%s' was thrown.",
                    feed_url_by_lang,
                    content.bozo_exception,
                )

            for entry in content.get("entries", []):
                url = entry.get("id")
                existed = (
                    bool(url)
                    and models.PressRelease.objects(url=url).first() is not None
                )
                try:
                    press_release = build_press_release(entry, journal, lang)
                    press_release.save()
                except ValidationError as exc:
                    logger.error(
                        "Could not save entry '%s', Please verify '%s'",
                        entry,
                        exc,
                    )
                else:
                    logger.info(
                        "Press Release '%s', saved successfully.",
                        press_release.title,
                    )
                    if not existed:
                        created_press_releases.append(press_release)
    return created_press_releases


def _run_sync(sync_news=True, sync_press_releases=True):
    created_news = []
    created_press_releases = []
    if sync_news:
        created_news = try_fetch_and_register_news_feed(
            current_app.config["RSS_NEWS_FEEDS"]
        )
    if sync_press_releases:
        created_press_releases = try_fetch_and_register_press_release_feed(
            current_app.config["RSS_PRESS_RELEASES_FEEDS"]
        )
    send_sync_notification(created_news, created_press_releases)


def _with_app_context(callback):
    if has_app_context():
        return callback()
    flask_app = webapp.create_app()
    with flask_app.app_context():
        return callback()


def sync_external_content():
    """RQ/CLI: sync news and press-releases from configured RSS feeds."""
    _with_app_context(lambda: _run_sync(True, True))


def sync_rss_news():
    """CLI: sync news feeds only."""
    _with_app_context(lambda: _run_sync(True, False))


def sync_rss_press_releases():
    """CLI: sync press-release feeds only."""
    _with_app_context(lambda: _run_sync(False, True))
