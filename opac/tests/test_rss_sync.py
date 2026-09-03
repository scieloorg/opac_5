# coding: utf-8

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from flask import current_app
from mongoengine.errors import ValidationError
from opac_schema.v1.models import News, PressRelease
from tenacity import RetryError
from webapp import controllers, rss_sync
from webapp.utils import NonRetryableError

from . import utils
from .base import BaseTestCase

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_json_fixture(name):
    with open(FIXTURES / name, encoding="utf-8") as fh:
        return json.load(fh)


class ExtractImageUrlTests(BaseTestCase):
    def test_uses_last_media_content_url(self):
        entry = {
            "media_content": [
                {"url": "https://blog.scielo.org/wp-content/first.jpg"},
                {"url": "https://blog.scielo.org/wp-content/image.jpg"},
            ]
        }
        self.assertEqual(
            rss_sync.extract_image_url(entry),
            "https://blog.scielo.org/wp-content/image.jpg",
        )

    def test_falls_back_to_enclosure_link(self):
        entry = {
            "links": [
                {
                    "rel": "alternate",
                    "type": "text/html",
                    "href": "https://blog.scielo.org/post",
                },
                {
                    "rel": "enclosure",
                    "type": "image/jpeg",
                    "href": "https://example.com/pic.jpg",
                },
            ]
        }
        self.assertEqual(
            rss_sync.extract_image_url(entry), "https://example.com/pic.jpg"
        )

    def test_falls_back_to_img_src_in_summary(self):
        entry = {
            "summary": '<p>Hello <img src="https://example.com/from-html.jpg" alt="x"/></p>'
        }
        self.assertEqual(
            rss_sync.extract_image_url(entry),
            "https://example.com/from-html.jpg",
        )

    def test_falls_back_to_img_src_in_content(self):
        entry = {"content": [{"value": '<img src="https://example.com/content.jpg"/>'}]}
        self.assertEqual(
            rss_sync.extract_image_url(entry),
            "https://example.com/content.jpg",
        )

    def test_returns_none_when_no_image(self):
        self.assertIsNone(rss_sync.extract_image_url({"summary": "no image"}))


class ParsePublicationDateTests(BaseTestCase):
    def test_parses_rfc822_published_slice(self):
        entry = {"published": "Wed, 29 Jan 2020 17:45:29 +0000"}
        self.assertEqual(
            rss_sync.parse_publication_date(entry),
            datetime(2020, 1, 29, 17, 45, 29),
        )

    def test_invalid_published_uses_now(self):
        before = datetime.now()
        result = rss_sync.parse_publication_date({"published": "not-a-date"})
        after = datetime.now()
        self.assertGreaterEqual(result, before)
        self.assertLessEqual(result, after)

    def test_missing_published_uses_now(self):
        result = rss_sync.parse_publication_date({})
        self.assertIsInstance(result, datetime)


class BuildNewsTests(BaseTestCase):
    def test_news_from_fixture_maps_fields_and_image(self):
        entry = load_json_fixture("rss-news-feed.json")[0]
        news = controllers.build_news(entry, "en")

        self.assertIsNotNone(news._id)
        self.assertEqual(32, len(news._id))
        self.assertEqual("Random title", news.title)
        self.assertEqual("Summary..", news.description)
        self.assertEqual("https://blog.scielo.org/wp-content/image.jpg", news.image_url)
        self.assertEqual("en", news.language)
        self.assertEqual("http://blog.scielo.org/?p=5060", news.url)
        self.assertEqual(news.publication_date, datetime(2020, 1, 29, 17, 45, 29))

    def test_upsert_by_url_keeps_id_and_updates_title(self):
        entry = load_json_fixture("rss-news-feed.json")[0]
        first = controllers.build_news(entry, "en")
        first.save()
        first_id = first._id

        updated_entry = dict(entry)
        updated_entry["title"] = "Updated title"
        second = controllers.build_news(updated_entry, "en")
        second.save()

        self.assertEqual(News.objects.count(), 1)
        saved = News.objects.get(url=entry["id"])
        self.assertEqual(saved._id, first_id)
        self.assertEqual(saved.title, "Updated title")

    def test_image_url_none_when_entry_has_no_image(self):
        entry = {
            "id": "https://blog.scielo.org/?p=1",
            "title": "No image",
            "summary": "text only",
            "published": "Wed, 29 Jan 2020 17:45:29 +0000",
        }
        news = controllers.build_news(entry, "pt_BR")
        self.assertIsNone(news.image_url)


class BuildPressReleaseTests(BaseTestCase):
    def test_press_release_maps_fields_including_image_url(self):
        entry = load_json_fixture("rss-press-release-feed.json")[0]
        journal = utils.makeOneJournal({"acronym": "rae", "current_status": "current"})
        press_release = controllers.build_press_release(entry, journal, "pt_BR")

        self.assertIsNotNone(press_release._id)
        self.assertEqual(32, len(press_release._id))
        self.assertEqual(
            "Como os memes da internet conectam diferentes mundos?",
            press_release.title,
        )
        self.assertEqual(
            "Que se destacou na internet e outras....", press_release.content
        )
        self.assertEqual("pt_BR", press_release.language)
        self.assertEqual(journal, press_release.journal)
        self.assertEqual(
            "https://pressreleases.scielo.org/wp-content/uploads/2017/09/rae_logo_thumb.jpg",
            press_release.image_url,
        )


class FetchRssTests(BaseTestCase):
    @patch("webapp.rss_sync.fetch_data")
    def test_fetch_rss_uses_fetch_data_with_user_agent(self, mock_fetch_data):
        mock_fetch_data.return_value = b""
        rss_sync.fetch_rss("https://blog.scielo.org/feed/")
        mock_fetch_data.assert_called_once_with(
            "https://blog.scielo.org/feed/",
            headers=rss_sync.RSS_SYNC_HEADERS,
            timeout=10,
        )


class RegisterNewsFeedTests(BaseTestCase):
    def _xml_content(self, filename="rss-news-feed.xml"):
        return (FIXTURES / filename).read_bytes()

    @patch("webapp.rss_sync.fetch_rss")
    def test_persists_valid_news_with_image_and_skips_invalid(self, mock_fetch):
        mock_fetch.return_value = self._xml_content()
        created = rss_sync.try_fetch_and_register_news_feed(
            {"pt_BR": {"url": "https://blog.scielo.org/feed/"}}
        )

        self.assertEqual(News.objects.count(), 1)
        self.assertEqual(len(created), 1)
        news = News.objects.first()
        self.assertEqual(news.title, "News with image")
        self.assertEqual(news.language, "pt_BR")
        self.assertEqual(news.image_url, "https://blog.scielo.org/wp-content/image.jpg")
        self.assertEqual(news.url, "https://blog.scielo.org/?p=5060")
        self.assertEqual(created[0].url, news.url)

    @patch("webapp.rss_sync.fetch_rss")
    def test_second_run_does_not_report_existing_news_as_new(self, mock_fetch):
        mock_fetch.return_value = self._xml_content()
        feeds = {"pt_BR": {"url": "https://blog.scielo.org/feed/"}}
        first = rss_sync.try_fetch_and_register_news_feed(feeds)
        second = rss_sync.try_fetch_and_register_news_feed(feeds)

        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertEqual(News.objects.count(), 1)

    @patch("webapp.rss_sync.fetch_rss")
    def test_http_error_skips_feed(self, mock_fetch):
        mock_fetch.side_effect = NonRetryableError("HTTP 403")
        rss_sync.try_fetch_and_register_news_feed(
            {"en": {"url": "https://blog.scielo.org/en/feed/"}}
        )
        self.assertEqual(News.objects.count(), 0)

    @patch("webapp.rss_sync.fetch_rss")
    def test_retry_error_skips_feed_and_continues(self, mock_fetch):
        mock_fetch.side_effect = [
            RetryError(Mock()),
            self._xml_content(),
        ]
        rss_sync.try_fetch_and_register_news_feed(
            {
                "es": {"url": "https://blog.scielo.org/es/feed/"},
                "pt_BR": {"url": "https://blog.scielo.org/feed/"},
            }
        )
        self.assertEqual(News.objects.count(), 1)
        self.assertEqual(News.objects.first().language, "pt_BR")

    @patch("webapp.rss_sync.controllers.build_news")
    @patch("webapp.rss_sync.feedparser.parse")
    @patch("webapp.rss_sync.fetch_rss")
    def test_validation_error_does_not_abort_batch(
        self, mock_fetch, mock_parse, mock_build
    ):
        mock_fetch.return_value = b"<rss/>"
        parsed = Mock(bozo=0)
        parsed.get.return_value = [{"id": "a"}, {"id": "b"}]
        mock_parse.return_value = parsed

        valid = Mock()
        mock_build.side_effect = [ValidationError("bad"), valid]

        rss_sync.try_fetch_and_register_news_feed(
            {"en": {"url": "https://blog.scielo.org/en/feed/"}}
        )

        valid.save.assert_called_once_with()


class RegisterPressReleaseFeedTests(BaseTestCase):
    @patch("webapp.rss_sync.fetch_rss")
    def test_fetches_only_public_current_journals_and_formats_urls(self, mock_fetch):
        utils.makeOneJournal(
            {"acronym": "rae", "is_public": True, "current_status": "current"}
        )
        utils.makeOneJournal(
            {"acronym": "old", "is_public": True, "current_status": "deceased"}
        )
        utils.makeOneJournal(
            {"acronym": "priv", "is_public": False, "current_status": "current"}
        )
        mock_fetch.return_value = (
            FIXTURES / "rss-press-release-feed.xml"
        ).read_bytes()

        created = rss_sync.try_fetch_and_register_press_release_feed(
            current_app.config["RSS_PRESS_RELEASES_FEEDS"]
        )

        called_urls = [call.args[0] for call in mock_fetch.call_args_list]
        self.assertEqual(len(called_urls), 3)
        self.assertIn(
            "https://pressreleases.scielo.org/blog/category/rae/feed/",
            called_urls,
        )
        self.assertIn(
            "https://pressreleases.scielo.org/es/category/press-releases/rae/feed/",
            called_urls,
        )
        self.assertIn(
            "https://pressreleases.scielo.org/en/category/press-releases/rae/feed/",
            called_urls,
        )
        self.assertFalse(
            any("/old/" in url or url.endswith("/old/feed/") for url in called_urls)
        )
        self.assertFalse(any("priv" in url for url in called_urls))

        self.assertEqual(PressRelease.objects.count(), 1)
        press_release = PressRelease.objects.first()
        self.assertEqual(
            press_release.title,
            "Como os memes da internet conectam diferentes mundos?",
        )
        self.assertEqual(
            press_release.image_url,
            "https://pressreleases.scielo.org/wp-content/uploads/2017/09/rae_logo_thumb.jpg",
        )
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].url, press_release.url)

    @patch("webapp.rss_sync.fetch_rss")
    def test_second_run_does_not_report_existing_press_release_as_new(self, mock_fetch):
        utils.makeOneJournal(
            {"acronym": "rae", "is_public": True, "current_status": "current"}
        )
        mock_fetch.return_value = (
            FIXTURES / "rss-press-release-feed.xml"
        ).read_bytes()
        feeds = current_app.config["RSS_PRESS_RELEASES_FEEDS"]
        first = rss_sync.try_fetch_and_register_press_release_feed(feeds)
        second = rss_sync.try_fetch_and_register_press_release_feed(feeds)
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertEqual(PressRelease.objects.count(), 1)


class SyncExternalContentTests(BaseTestCase):
    def test_default_feed_urls_use_https(self):
        news_feeds = current_app.config["RSS_NEWS_FEEDS"]
        pr_feeds = current_app.config["RSS_PRESS_RELEASES_FEEDS"]
        for feed in news_feeds.values():
            self.assertTrue(feed["url"].startswith("https://"))
        for feed in pr_feeds.values():
            self.assertTrue(feed["url"].startswith("https://"))
        self.assertEqual(current_app.config["RSS_SYNC_CRON_STRING"], "0 12 * * 1,3,5")
        self.assertEqual(current_app.config["RSS_SYNC_QUEUE_NAME"], "syncexternalcontent")
        self.assertEqual(
            current_app.config["RSS_SYNC_NOTIFICATION_RECIPIENTS"],
            ["tecnologia@scielo.org"],
        )

    @patch("webapp.rss_sync.send_sync_notification")
    @patch("webapp.rss_sync.try_fetch_and_register_press_release_feed")
    @patch("webapp.rss_sync.try_fetch_and_register_news_feed")
    @patch("webapp.rss_sync.webapp.create_app")
    def test_sync_external_content_reuses_existing_app_context(
        self, mock_create_app, mock_news, mock_pr, mock_notify
    ):
        created_news = [Mock(title="News with image")]
        created_prs = [Mock(title="PR title")]
        mock_news.return_value = created_news
        mock_pr.return_value = created_prs
        rss_sync.sync_external_content()
        mock_create_app.assert_not_called()
        mock_news.assert_called_once_with(self.app.config["RSS_NEWS_FEEDS"])
        mock_pr.assert_called_once_with(self.app.config["RSS_PRESS_RELEASES_FEEDS"])
        mock_notify.assert_called_once_with(created_news, created_prs)

    @patch("webapp.rss_sync.send_sync_notification")
    @patch("webapp.rss_sync.try_fetch_and_register_press_release_feed")
    @patch("webapp.rss_sync.try_fetch_and_register_news_feed")
    @patch("webapp.rss_sync.webapp.create_app")
    @patch("webapp.rss_sync.has_app_context", return_value=False)
    def test_sync_external_content_creates_app_without_context(
        self, mock_has_ctx, mock_create_app, mock_news, mock_pr, mock_notify
    ):
        mock_create_app.return_value = self.app
        created_news = [Mock(title="News with image")]
        created_prs = []
        mock_news.return_value = created_news
        mock_pr.return_value = created_prs
        rss_sync.sync_external_content()
        mock_create_app.assert_called_once_with()
        mock_news.assert_called_once_with(self.app.config["RSS_NEWS_FEEDS"])
        mock_notify.assert_called_once_with(created_news, created_prs)

    @patch("webapp.rss_sync.send_sync_notification")
    @patch("webapp.rss_sync.try_fetch_and_register_press_release_feed")
    @patch("webapp.rss_sync.try_fetch_and_register_news_feed")
    def test_sync_rss_news_skips_press_releases(
        self, mock_news, mock_pr, mock_notify
    ):
        created_news = [Mock(title="News with image")]
        mock_news.return_value = created_news
        rss_sync.sync_rss_news()
        mock_news.assert_called_once_with(self.app.config["RSS_NEWS_FEEDS"])
        mock_pr.assert_not_called()
        mock_notify.assert_called_once_with(created_news, [])

    @patch("webapp.rss_sync.send_sync_notification")
    @patch("webapp.rss_sync.try_fetch_and_register_press_release_feed")
    @patch("webapp.rss_sync.try_fetch_and_register_news_feed")
    def test_sync_rss_press_releases_skips_news(
        self, mock_news, mock_pr, mock_notify
    ):
        created_prs = [Mock(title="PR title")]
        mock_pr.return_value = created_prs
        rss_sync.sync_rss_press_releases()
        mock_news.assert_not_called()
        mock_pr.assert_called_once_with(self.app.config["RSS_PRESS_RELEASES_FEEDS"])
        mock_notify.assert_called_once_with([], created_prs)


class NewNewsNotificationTests(BaseTestCase):
    def _make_news(self):
        return Mock(
            title="News with image",
            url="https://blog.scielo.org/?p=5060",
            language="pt_BR",
            publication_date=datetime(2020, 1, 29, 17, 45, 29),
        )

    def _make_press_release(self):
        return Mock(
            title="PR title",
            url="https://pressreleases.scielo.org/?p=2246",
            language="pt_BR",
            publication_date=datetime(2019, 11, 26, 17, 0, 40),
            journal=Mock(acronym="rae"),
        )

    @patch("webapp.rss_sync.send_email")
    def test_sends_email_listing_new_news(self, mock_send_email):
        mock_send_email.return_value = (True, "")
        news = self._make_news()

        rss_sync.send_sync_notification([news], [])

        mock_send_email.assert_called_once()
        recipients, subject, html = mock_send_email.call_args[0]
        self.assertEqual(recipients, ["tecnologia@scielo.org"])
        self.assertIn("1 notícia(s) nova(s)", subject)
        self.assertIn("News with image", html)
        self.assertIn("https://blog.scielo.org/?p=5060", html)
        self.assertIn("pt_BR", html)

    @patch("webapp.rss_sync.send_email")
    def test_sends_email_listing_new_press_releases(self, mock_send_email):
        mock_send_email.return_value = (True, "")
        press_release = self._make_press_release()

        rss_sync.send_sync_notification([], [press_release])

        mock_send_email.assert_called_once()
        recipients, subject, html = mock_send_email.call_args[0]
        self.assertEqual(recipients, ["tecnologia@scielo.org"])
        self.assertIn("1 press-release(s) novo(s)", subject)
        self.assertIn("PR title", html)
        self.assertIn("rae", html)
        self.assertIn("https://pressreleases.scielo.org/?p=2246", html)

    @patch("webapp.rss_sync.send_email")
    def test_sends_email_with_news_and_press_releases(self, mock_send_email):
        mock_send_email.return_value = (True, "")
        rss_sync.send_sync_notification(
            [self._make_news()], [self._make_press_release()]
        )
        recipients, subject, html = mock_send_email.call_args[0]
        self.assertIn("1 notícia(s) nova(s)", subject)
        self.assertIn("1 press-release(s) novo(s)", subject)
        self.assertIn("News with image", html)
        self.assertIn("PR title", html)

    @patch("webapp.rss_sync.send_email")
    def test_does_not_send_email_when_there_are_no_new_items(self, mock_send_email):
        rss_sync.send_sync_notification([], [])
        mock_send_email.assert_not_called()

    @patch("webapp.rss_sync.send_email")
    def test_does_not_send_email_when_notification_disabled(self, mock_send_email):
        original = current_app.config["RSS_SYNC_NOTIFICATION_ENABLED"]
        current_app.config["RSS_SYNC_NOTIFICATION_ENABLED"] = False
        try:
            rss_sync.send_sync_notification([self._make_news()], [])
        finally:
            current_app.config["RSS_SYNC_NOTIFICATION_ENABLED"] = original
        mock_send_email.assert_not_called()
