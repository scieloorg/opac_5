# coding: utf-8
"""Targeted tests to reach full line+branch coverage of webapp.controllers."""

import datetime
import json
import os
from unittest.mock import MagicMock, Mock, PropertyMock, patch
from uuid import uuid4

from flask import current_app
from flask_babel import gettext as __
from opac_schema.v1.models import Article, Issue, News, PressRelease
from webapp import controllers
from webapp.controllers import ArticleJournalNotFoundError

from . import utils
from .base import BaseTestCase

FIXTURES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


class FixPidCoverageTests(BaseTestCase):
    def test_fix_pid_replaces_known_issn(self):
        self.assertEqual(
            controllers._fix_pid("S0102-7638(99)00001"),
            "S1678-9741(99)00001",
        )

    def test_fix_pid_returns_original_when_no_match(self):
        self.assertEqual(controllers._fix_pid("S0000-0000(99)00001"), "S0000-0000(99)00001")


class CollectionCoverageTests(BaseTestCase):
    def test_get_current_collection_falls_back_when_config_missing(self):
        utils.makeOneCollection({"acronym": "fallback"})
        previous = current_app.config.pop("OPAC_COLLECTION")
        try:
            result = controllers.get_current_collection()
            self.assertEqual(result.acronym, "fallback")
        finally:
            current_app.config["OPAC_COLLECTION"] = previous

    @patch("webapp.controllers.tweepy.API")
    @patch("webapp.controllers.tweepy.OAuthHandler")
    def test_get_collection_tweets_returns_parsed_tweets(self, mock_auth_cls, mock_api_cls):
        tweet = Mock()
        tweet.id = 99
        tweet.user.screen_name = "scielo"
        tweet.full_text = "tweet body"
        tweet.entities = {"media": [{"media_url_https": "https://img.test/t.png"}]}

        mock_api = mock_api_cls.return_value
        mock_api.user_timeline.return_value = [tweet]

        result = controllers.get_collection_tweets()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["media_url_https"], "https://img.test/t.png")

    @patch("webapp.controllers.tweepy.API")
    @patch("webapp.controllers.tweepy.OAuthHandler")
    def test_get_collection_tweets_returns_empty_on_attribute_error(
        self, mock_auth_cls, mock_api_cls
    ):
        tweet = Mock(spec=[])
        mock_api_cls.return_value.user_timeline.return_value = [tweet]
        self.assertEqual(controllers.get_collection_tweets(), [])

    @patch("webapp.controllers.tweepy.API", side_effect=RuntimeError("twitter down"))
    @patch("webapp.controllers.tweepy.OAuthHandler")
    def test_get_collection_tweets_returns_empty_on_api_error(
        self, mock_auth_cls, mock_api_cls
    ):
        self.assertEqual(controllers.get_collection_tweets(), [])

    def test_get_collection_tweets_returns_empty_without_credentials(self):
        keys = [
            "TWITTER_CONSUMER_KEY",
            "TWITTER_CONSUMER_SECRET",
            "TWITTER_ACCESS_TOKEN",
            "TWITTER_ACCESS_TOKEN_SECRET",
        ]
        saved = {key: current_app.config.get(key) for key in keys}
        try:
            current_app.config["TWITTER_CONSUMER_KEY"] = ""
            self.assertEqual(controllers.get_collection_tweets(), [])
        finally:
            current_app.config.update(saved)


class PressReleaseCoverageTests(BaseTestCase):
    def _make_press_release(self, **kwargs):
        journal = kwargs.get("journal") or utils.makeOneJournal()
        issue = kwargs.get("issue") or utils.makeOneIssue({"journal": journal})
        article = kwargs.get("article") or utils.makeOneArticle(
            {"journal": journal, "issue": issue}
        )
        return PressRelease(
            _id=str(uuid4().hex),
            title=kwargs.get("title", "PR"),
            language=kwargs.get("language", "pt"),
            content=kwargs.get("content", "<p>content</p>"),
            journal=journal.id,
            issue=issue.id,
            article=article.id,
            url=kwargs.get("url", "http://example.com/pr"),
            publication_date=kwargs.get(
                "publication_date", datetime.datetime(2024, 1, 1)
            ),
        ).save()

    def _bundle(self):
        journal = utils.makeOneJournal()
        issue = utils.makeOneIssue({"journal": journal})
        article = utils.makeOneArticle({"journal": journal, "issue": issue})
        return journal, issue, article

    def test_get_press_release_with_article_filter(self):
        journal, issue, article = self._bundle()
        pr = self._make_press_release(journal=journal, issue=issue, article=article)

        result = controllers.get_press_release(journal, issue, "pt", article=article)
        self.assertEqual(result.id, pr.id)

    def test_get_press_releases_with_default_filter(self):
        self._make_press_release(language="en")
        self.assertEqual(controllers.get_press_releases().count(), 1)


class JournalLookupCoverageTests(BaseTestCase):
    def test_get_journals_invalid_query_filter_raises(self):
        with self.assertRaises(ValueError):
            controllers.get_journals(query_filter="invalid")

    def test_get_journals_paginated_returns_pagination(self):
        utils.makeOneJournal({"title": "Alpha Journal"})
        pagination = controllers.get_journals_paginated("", page=1, per_page=10)
        self.assertEqual(pagination.total, 1)
        self.assertEqual(len(pagination.items), 1)

    def test_get_journal_json_data_includes_next_journal_link(self):
        journal = utils.makeOneJournal(
            {
                "last_issue": utils.getLastIssue(),
                "url_segment": "current-journal",
            }
        )
        with patch.object(
            type(journal), "url_next_journal", new_callable=PropertyMock
        ) as mock_next:
            mock_next.return_value = "next-journal"
            with current_app.test_request_context("/"):
                data = controllers.get_journal_json_data(journal)
        self.assertIn("url_next_journal", data)

    def test_get_alpha_list_from_paginated_journals(self):
        utils.makeOneJournal({"title": "Beta Journal"})
        result = controllers.get_alpha_list_from_paginated_journals("", page=1, per_page=5)
        self.assertEqual(result["total"], 1)
        self.assertEqual(len(result["journals"]), 1)

    def test_get_journals_grouped_by_skips_journals_without_grouper(self):
        utils.makeOneJournal({"publisher_name": ""})
        grouped = controllers.get_journals_grouped_by("publisher_name")
        self.assertEqual(grouped["meta"]["total"], 1)
        self.assertEqual(grouped["objects"], {})

    def test_get_journal_by_acron_requires_acronym(self):
        with self.assertRaises(ValueError) as exc:
            controllers.get_journal_by_acron("")
        self.assertEqual(str(exc.exception), __("Obrigatório um acronym."))

    def test_get_journal_by_url_seg_requires_url_seg(self):
        with self.assertRaises(ValueError) as exc:
            controllers.get_journal_by_url_seg("")
        self.assertEqual(str(exc.exception), __("Obrigatório um url_seg."))

    def test_get_journal_by_issn_requires_issn(self):
        with self.assertRaises(ValueError) as exc:
            controllers.get_journal_by_issn("")
        self.assertEqual(str(exc.exception), __("Obrigatório um issn."))

    def test_get_journal_by_title_requires_title(self):
        with self.assertRaises(ValueError) as exc:
            controllers.get_journal_by_title("")
        self.assertEqual(str(exc.exception), __("Obrigatório um title."))

    def test_get_journal_by_title_returns_journal(self):
        journal = utils.makeOneJournal({"title": "Unique Title"})
        self.assertEqual(controllers.get_journal_by_title("Unique Title").id, journal.id)


class IssueGridAndNavCoverageTests(BaseTestCase):
    def _make_grid_bundle(self):
        journal = utils.makeOneJournal()
        regular = utils.makeOneIssue(
            {
                "journal": journal,
                "type": "regular",
                "year": 2020,
                "volume": "10",
                "number": "2",
                "order": "2",
                "url_segment": "2020.v10n2",
            }
        )
        ahead = utils.makeOneIssue(
            {
                "journal": journal,
                "type": "ahead",
                "year": 2021,
                "number": "ahead",
                "order": "3",
                "url_segment": "2021.ahead",
            }
        )
        volume_issue = utils.makeOneIssue(
            {
                "journal": journal,
                "type": "volume_issue",
                "year": 2019,
                "volume": "9",
                "number": "1",
                "order": "1",
                "url_segment": "2019.v9",
            }
        )
        for issue in (regular, ahead, volume_issue):
            utils.makeOneArticle({"journal": journal, "issue": issue, "is_public": True})
        return journal, regular, ahead, volume_issue

    def test_get_issues_by_jid_filters_by_public_articles(self):
        journal, regular, ahead, volume_issue = self._make_grid_bundle()
        issues = list(controllers.get_issues_by_jid(journal.id))
        self.assertEqual(len(issues), 3)

    def test_get_issues_for_grid_by_jid_builds_volume_issue_map(self):
        journal, regular, ahead, volume_issue = self._make_grid_bundle()
        result = controllers.get_issues_for_grid_by_jid(journal.id)
        self.assertIn("result_dict", result)
        self.assertIn(volume_issue.volume, result["volume_issue"])
        self.assertEqual(result["ahead"].id, ahead.id)

    def test_get_issues_for_grid_by_jid_without_regular_issues(self):
        journal = utils.makeOneJournal()
        ahead = utils.makeOneIssue(
            {"journal": journal, "type": "ahead", "number": "ahead", "year": 2022}
        )
        utils.makeOneArticle({"journal": journal, "issue": ahead, "is_public": True})
        result = controllers.get_issues_for_grid_by_jid(journal.id)
        self.assertEqual(result["ordered_for_grid"], {})

    def test_get_issue_nav_bar_data_without_journal_raises(self):
        with self.assertRaises(ArticleJournalNotFoundError):
            controllers.get_issue_nav_bar_data()

    def test_get_issue_nav_bar_data_without_issue_returns_last_and_ahead(self):
        journal, regular, ahead, volume_issue = self._make_grid_bundle()
        result = controllers.get_issue_nav_bar_data(journal=journal)
        self.assertIsNone(result["issue"])
        self.assertEqual(result["previous_item"].id, regular.id)
        self.assertEqual(result["next_item"].id, ahead.id)

    def test_get_issue_nav_bar_data_for_ahead_issue(self):
        journal, regular, ahead, volume_issue = self._make_grid_bundle()
        result = controllers.get_issue_nav_bar_data(journal=journal, issue=ahead)
        self.assertEqual(result["issue"].id, ahead.id)
        self.assertIsNone(result["next_item"])

    def test_get_issue_nav_bar_data_returns_previous_and_next(self):
        journal = utils.makeOneJournal()
        older = utils.makeOneIssue(
            {
                "journal": journal,
                "type": "regular",
                "year": 2018,
                "order": "1",
                "number": "1",
            }
        )
        newer = utils.makeOneIssue(
            {
                "journal": journal,
                "type": "regular",
                "year": 2019,
                "order": "2",
                "number": "2",
            }
        )
        for issue in (older, newer):
            utils.makeOneArticle({"journal": journal, "issue": issue, "is_public": True})
        result = controllers.get_issue_nav_bar_data(journal=journal, issue=older)
        self.assertEqual(result["next_item"].id, newer.id)
        result = controllers.get_issue_nav_bar_data(journal=journal, issue=newer)
        self.assertEqual(result["previous_item"].id, older.id)

    def test_get_issue_by_label_requires_label(self):
        journal = utils.makeOneJournal()
        with self.assertRaises(ValueError) as exc:
            controllers.get_issue_by_label(journal.id, "")
        self.assertEqual(str(exc.exception), __("Obrigatório um label do issue."))

    def test_get_issue_by_acron_issue(self):
        journal = utils.makeOneJournal({"acronym": "abc"})
        issue = utils.makeOneIssue(
            {"journal": journal, "year": 2020, "label": "v1n1"}
        )
        result = controllers.get_issue_by_acron_issue("abc", "2020", "v1n1")
        self.assertEqual(result.id, issue.id)

    def test_get_issue_by_acron_issue_raises_when_missing_acronym(self):
        with self.assertRaises(ValueError) as exc:
            controllers.get_issue_by_acron_issue("", "2020", "v1n1")
        self.assertEqual(str(exc.exception), __("Obrigatório um acronym."))

    def test_get_issue_by_url_seg_requires_url_seg(self):
        with self.assertRaises(ValueError) as exc:
            controllers.get_issue_by_url_seg("", "issue-seg")
        self.assertEqual(str(exc.exception), __("Obrigatório um url_seg."))

    def test_get_issue_by_pid_requires_pid(self):
        with self.assertRaises(ValueError) as exc:
            controllers.get_issue_by_pid("")
        self.assertEqual(str(exc.exception), __("Obrigatório um PID."))

    def test_get_issue_by_url_seg_returns_issue(self):
        journal = utils.makeOneJournal({"acronym": "jour"})
        issue = utils.makeOneIssue({"journal": journal, "type": "regular"})
        result = controllers.get_issue_by_url_seg(
            journal.url_segment, issue.url_segment
        )
        self.assertEqual(result.id, issue.id)


class IssueAssetsCodeCoverageTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.journal = utils.makeOneJournal()

    def test_get_issue_info_from_assets_code_ahead(self):
        query = controllers.get_issue_info_from_assets_code("2020nahead", self.journal)
        self.assertIn("ahead", str(query))

    def test_get_issue_info_from_assets_code_volume_number(self):
        query = controllers.get_issue_info_from_assets_code("v10n2", self.journal)
        self.assertIn("10", str(query))

    def test_get_issue_info_from_assets_code_volume_number_supplement(self):
        query = controllers.get_issue_info_from_assets_code("v10n2s3", self.journal)
        self.assertIn("suppl_text", str(query))

    def test_get_issue_info_from_assets_code_volume_supplement_only(self):
        query = controllers.get_issue_info_from_assets_code("v10s3", self.journal)
        self.assertIn("suppl_text", str(query))

    def test_get_issue_info_from_assets_code_volume_only(self):
        query = controllers.get_issue_info_from_assets_code("v10", self.journal)
        self.assertIn("10", str(query))


class LastIssueCoverageTests(BaseTestCase):
    def test_set_last_issue_and_issue_count_updates_journal(self):
        journal = utils.makeOneJournal({"issue_count": 0})
        issue = utils.makeOneIssue(
            {
                "journal": journal,
                "type": "regular",
                "url_segment": "2020.v1n1",
                "year": 2020,
                "volume": "1",
                "number": "1",
            }
        )
        utils.makeOneArticle({"journal": journal, "issue": issue, "is_public": True})
        result = controllers.set_last_issue_and_issue_count(journal, issue)
        self.assertEqual(result.issue_count, 1)
        self.assertEqual(result.last_issue.url_segment, issue.url_segment)

    def test_set_last_issue_and_issue_count_returns_early_when_complete(self):
        journal = utils.makeOneJournal(
            {
                "issue_count": 2,
                "last_issue": utils.getLastIssue({"url_segment": "done"}),
            }
        )
        result = controllers.set_last_issue_and_issue_count(journal)
        self.assertEqual(result.issue_count, 2)

    @patch(
        "webapp.controllers.get_journal_issues_which_content_is_public",
        side_effect=RuntimeError("boom"),
    )
    def test_set_last_issue_and_issue_count_logs_exception(self, mock_query):
        journal = utils.makeOneJournal({"issue_count": None, "last_issue": None})
        result = controllers.set_last_issue_and_issue_count(journal)
        self.assertEqual(result.id, journal.id)

    def test_create_last_issue_for_journal_returns_none_without_issue(self):
        journal = utils.makeOneJournal()
        self.assertIsNone(controllers.create_last_issue_for_journal(journal, None))

    def test_create_last_issue_for_journal_returns_none_without_url_segment(self):
        journal = utils.makeOneJournal()
        issue = utils.makeOneIssue({"url_segment": None})
        self.assertIsNone(controllers.create_last_issue_for_journal(journal, issue))

    def test_create_last_issue_for_journal_skips_when_url_segment_unchanged(self):
        journal = utils.makeOneJournal()
        last_issue = utils.getLastIssue()
        last_issue.url_segment = "same-seg"
        journal.last_issue = last_issue
        journal.save()
        issue = utils.makeOneIssue({"journal": journal, "url_segment": "same-seg"})
        issue.url_segment = "same-seg"
        controllers.create_last_issue_for_journal(journal, issue)
        self.assertEqual(journal.last_issue.url_segment, "same-seg")

    def test_journal_last_issues_yields_journals(self):
        journal = utils.makeOneJournal({"last_issue": None})
        issue = utils.makeOneIssue(
            {
                "journal": journal,
                "type": "regular",
                "url_segment": "2021.v2n1",
                "year": 2021,
                "volume": "2",
                "number": "1",
            }
        )
        utils.makeOneArticle({"journal": journal, "issue": issue, "is_public": True})
        results = list(controllers.journal_last_issues())
        self.assertTrue(any(item["journal"] == journal.jid for item in results))


class ArticleLookupCoverageTests(BaseTestCase):
    def test_get_article_by_aid_sets_missing_original_language(self):
        journal = utils.makeOneJournal({"is_public": True})
        issue = utils.makeOneIssue({"journal": journal, "is_public": True})
        article = utils.makeOneArticle(
            {
                "journal": journal,
                "issue": issue,
                "original_language": None,
                "languages": ["en"],
            }
        )
        result = controllers.get_article_by_aid(article.id, journal.url_segment)
        self.assertEqual(result.original_language, "en")

    def test_get_article_by_aid_handles_empty_languages(self):
        journal = utils.makeOneJournal({"is_public": True})
        issue = utils.makeOneIssue({"journal": journal, "is_public": True})
        article = utils.makeOneArticle(
            {
                "journal": journal,
                "issue": issue,
                "original_language": None,
                "languages": [],
            }
        )
        result = controllers.get_article_by_aid(article.id, journal.url_segment)
        self.assertIsNone(result.original_language)

    def test_get_article_navigation_for_ahead_issue(self):
        journal = utils.makeOneJournal(
            {"is_public": True, "url_segment": "ahead-journal"}
        )
        issue = utils.makeOneIssue(
            {
                "journal": journal,
                "is_public": True,
                "type": "ahead",
                "number": "ahead",
                "year": 2022,
            }
        )
        first = utils.makeOneArticle(
            {
                "journal": journal,
                "issue": issue,
                "order": "1",
                "publication_date": "2022-01-01",
            }
        )
        second = utils.makeOneArticle(
            {
                "journal": journal,
                "issue": issue,
                "order": "2",
                "publication_date": "2022-01-01",
            }
        )
        lang, article, nav = controllers.get_article(
            first.id, journal.url_segment, "pt", gs_abstract=False
        )
        self.assertEqual(article.id, first.id)
        self.assertEqual(nav["next_article"].id, second.id)

    def test_get_existing_lang_falls_back_to_first_language(self):
        article = utils.makeOneArticle({"languages": ["pt", "en"]})
        self.assertEqual(controllers.get_existing_lang(article, "fr", False), "pt")

    def test_get_existing_lang_uses_abstract_languages(self):
        article = utils.makeOneArticle({"abstract_languages": ["es"]})
        self.assertEqual(controllers.get_existing_lang(article, "pt", True), "es")

    def test_get_existing_lang_keeps_none_when_lang_missing(self):
        article = utils.makeOneArticle({"languages": ["pt"]})
        self.assertIsNone(controllers.get_existing_lang(article, None, False))

    def test_get_existing_lang_returns_none_when_no_languages(self):
        article = utils.makeOneArticle(
            {"original_language": "", "languages": []}
        )
        self.assertIsNone(controllers.get_existing_lang(article, "en", False))
        self.assertIsNone(controllers.get_existing_lang(article, "en", True))

    def test_get_article_by_url_seg_requires_segment(self):
        with self.assertRaises(ValueError) as exc:
            controllers.get_article_by_url_seg("")
        self.assertEqual(str(exc.exception), __("Obrigatório um url_seg_article."))

    def test_get_article_by_issue_article_seg_requires_iid(self):
        with self.assertRaises(ValueError) as exc:
            controllers.get_article_by_issue_article_seg("", "article-seg")
        self.assertEqual(str(exc.exception), __("Obrigatório um iid and url_seg_article."))

    def test_get_article_by_aop_url_segs_requires_all_segments(self):
        with self.assertRaises(ValueError) as exc:
            controllers.get_article_by_aop_url_segs("jid", "", "article-seg")
        self.assertEqual(
            str(exc.exception),
            __("Obrigatório um jid, url_seg_issue and url_seg_article."),
        )

    def test_set_article_display_full_text_bulk_requires_ids(self):
        with self.assertRaises(ValueError):
            controllers.set_article_display_full_text_bulk(None)

    def test_is_aop_issue_true_for_ahead_number(self):
        journal = utils.makeOneJournal()
        issue = utils.makeOneIssue({"journal": journal, "number": "ahead"})
        article = utils.makeOneArticle({"journal": journal, "issue": issue})
        queryset = Article.objects(issue=issue.id)
        self.assertTrue(controllers.is_aop_issue(queryset))

    def test_is_aop_issue_false_for_empty_queryset(self):
        self.assertFalse(controllers.is_aop_issue(Article.objects(_id="missing")))

    def test_is_open_issue_true_when_elocation_present(self):
        journal = utils.makeOneJournal()
        issue = utils.makeOneIssue({"journal": journal})
        utils.makeOneArticle(
            {"journal": journal, "issue": issue, "elocation": "e123"}
        )
        queryset = Article.objects(issue=issue.id)
        self.assertTrue(controllers.is_open_issue(queryset))

    def test_is_open_issue_false_for_empty_queryset(self):
        self.assertFalse(controllers.is_open_issue(Article.objects(_id="missing")))

    def test_get_article_by_pid_v1_requires_pid(self):
        with self.assertRaises(ValueError):
            controllers.get_article_by_pid_v1("")

    def test_get_article_by_pid_requires_pid(self):
        with self.assertRaises(ValueError):
            controllers.get_article_by_pid("")

    def test_get_article_by_oap_pid_requires_pid(self):
        with self.assertRaises(ValueError):
            controllers.get_article_by_oap_pid("")

    def test_get_article_by_pid_v2_requires_pid(self):
        with self.assertRaises(ValueError):
            controllers.get_article_by_pid_v2("")

    def test_get_article_by_pid_v2_uses_fixed_pid(self):
        journal = utils.makeOneJournal()
        issue = utils.makeOneIssue({"journal": journal})
        article = utils.makeOneArticle(
            {
                "journal": journal,
                "issue": issue,
                "pid": "S1678-9741(99)00001",
            }
        )
        result = controllers.get_article_by_pid_v2("S0102-7638(99)00001")
        self.assertEqual(result.id, article.id)

    def test_get_article_by_pid_v2_returns_none_when_not_found(self):
        self.assertIsNone(controllers.get_article_by_pid_v2("UNKNOWNPID"))

    def test_get_recent_articles_of_issue_requires_issue_iid(self):
        with self.assertRaises(ValueError):
            controllers.get_recent_articles_of_issue("")


class PdfAndSupplementCoverageTests(BaseTestCase):
    def test_get_article_by_pdf_filename_strips_lang_prefix(self):
        journal = utils.makeOneJournal({"acronym": "jsp"})
        issue = utils.makeOneIssue({"journal": journal, "label": "v1n1"})
        article = utils.makeOneArticle(
            {
                "journal": journal,
                "issue": issue,
                "pdfs": [
                    {
                        "lang": "en",
                        "filename": "article.pdf",
                        "url": "http://example.com/en.pdf",
                    }
                ],
            }
        )
        result = controllers.get_article_by_pdf_filename("jsp", "v1n1", "en_article.pdf")
        self.assertEqual(result.id, article.id)
        self.assertEqual(result._pdf_lang, "en")

    def test_get_article_by_pdf_filename_without_lang_prefix(self):
        journal = utils.makeOneJournal({"acronym": "jsp"})
        issue = utils.makeOneIssue({"journal": journal, "label": "v1n1"})
        article = utils.makeOneArticle(
            {
                "journal": journal,
                "issue": issue,
                "pdfs": [
                    {
                        "lang": "pt",
                        "filename": "article.pdf",
                        "url": "http://example.com/pt.pdf",
                    }
                ],
            }
        )
        result = controllers.get_article_by_pdf_filename("jsp", "v1n1", "article.pdf")
        self.assertEqual(result.id, article.id)
        self.assertEqual(result._pdf_url, "http://example.com/pt.pdf")

    def test_get_article_by_suppl_material_filename(self):
        journal = utils.makeOneJournal({"acronym": "jsp"})
        issue = utils.makeOneIssue({"journal": journal, "label": "v1n1"})
        article = utils.makeOneArticle(
            {
                "journal": journal,
                "issue": issue,
                "mat_suppl": [{"filename": "suppl.pdf", "url": "http://example.com/s.pdf"}],
            }
        )
        result = controllers.get_article_by_suppl_material_filename(
            "jsp", "v1n1", "suppl.pdf"
        )
        self.assertEqual(result.id, article.id)

    def test_get_article_by_suppl_material_filename_validation_errors(self):
        with self.assertRaises(ValueError):
            controllers.get_article_by_suppl_material_filename("", "v1n1", "suppl.pdf")
        with self.assertRaises(ValueError):
            controllers.get_article_by_suppl_material_filename("jsp", "", "suppl.pdf")
        with self.assertRaises(ValueError):
            controllers.get_article_by_suppl_material_filename("jsp", "v1n1", "")


class ArticleMaintenanceCoverageTests(BaseTestCase):
    def test_get_articles_by_date_range_with_journal_acronym(self):
        journal = utils.makeOneJournal({"acronym": "abc"})
        issue = utils.makeOneIssue({"journal": journal})
        article = utils.makeOneArticle(
            {
                "journal": journal,
                "issue": issue,
                "updated": datetime.datetime(2024, 5, 10, 12, 0, 0),
            }
        )
        pagination = controllers.get_articles_by_date_range(
            datetime.datetime(2024, 5, 1),
            datetime.datetime(2024, 5, 31),
            journal_acronym="abc",
        )
        self.assertEqual(pagination.total, 1)
        self.assertEqual(pagination.items[0].id, article.id)

    def test_get_articles_by_date_range_with_unknown_acronym(self):
        pagination = controllers.get_articles_by_date_range(
            datetime.datetime(2024, 5, 1),
            datetime.datetime(2024, 5, 31),
            journal_acronym="missing",
        )
        self.assertEqual(pagination.total, 0)

    def test_get_articles_by_date_range_with_journal_id(self):
        journal = utils.makeOneJournal()
        issue = utils.makeOneIssue({"journal": journal})
        article = utils.makeOneArticle(
            {
                "journal": journal,
                "issue": issue,
                "updated": datetime.datetime(2024, 6, 10, 12, 0, 0),
            }
        )
        pagination = controllers.get_articles_by_date_range(
            datetime.datetime(2024, 6, 1),
            datetime.datetime(2024, 6, 30),
            journal_id=journal.id,
        )
        self.assertEqual(pagination.items[0].id, article.id)

    def test_delete_articles_by_iid_requires_issue_id(self):
        with self.assertRaises(ValueError):
            controllers.delete_articles_by_iid("")

    def test_delete_articles_by_iid_with_keep_list(self):
        journal = utils.makeOneJournal()
        issue = utils.makeOneIssue({"journal": journal})
        keep = utils.makeOneArticle({"journal": journal, "issue": issue, "_id": "keep"})
        remove = utils.makeOneArticle({"journal": journal, "issue": issue, "_id": "drop"})
        removed = controllers.delete_articles_by_iid(issue.id, keep_list=["keep"])
        self.assertEqual(removed, ["drop"])
        self.assertIsNotNone(Article.objects.get(_id="keep"))
        with self.assertRaises(Article.DoesNotExist):
            Article.objects.get(_id="drop")

    def test_delete_articles_by_iid_without_keep_list(self):
        journal = utils.makeOneJournal()
        issue = utils.makeOneIssue({"journal": journal})
        utils.makeOneArticle({"journal": journal, "issue": issue, "_id": "gone"})
        removed = controllers.delete_articles_by_iid(issue.id)
        self.assertEqual(removed, ["gone"])


class NewsAndPressReleaseRecordCoverageTests(BaseTestCase):
    def test_create_news_record(self):
        controllers.create_news_record(
            {
                "title": "News",
                "description": "desc",
                "url": "http://example.com",
                "language": "pt",
                "is_public": True,
                "publication_date": datetime.datetime(2024, 1, 1),
            }
        )
        self.assertEqual(News.objects.count(), 1)

    def test_create_news_record_reraises_exception(self):
        with self.assertRaises(Exception):
            controllers.create_news_record({})

    def test_create_press_release_record_creates_new(self):
        journal = utils.makeOneJournal()
        issue = utils.makeOneIssue({"journal": journal})
        article = utils.makeOneArticle({"journal": journal, "issue": issue})
        controllers.create_press_release_record(
            {
                "title": "PR",
                "language": "pt",
                "content": "<p>x</p>",
                "journal": journal,
                "issue": issue,
                "article": article,
                "url": "http://example.com/pr",
                "publication_date": datetime.datetime(2024, 1, 1),
            }
        )
        self.assertEqual(PressRelease.objects.count(), 1)

    def test_create_press_release_record_updates_existing(self):
        journal = utils.makeOneJournal()
        issue = utils.makeOneIssue({"journal": journal})
        article = utils.makeOneArticle({"journal": journal, "issue": issue})
        data = {
            "title": "PR title",
            "language": "pt",
            "content": "<p>content</p>",
            "journal": journal,
            "issue": issue,
            "article": article,
            "url": "http://example.com/pr",
            "publication_date": datetime.datetime(2024, 1, 1),
        }
        controllers.create_press_release_record(data)
        first_id = PressRelease.objects.first().id
        controllers.create_press_release_record(data)
        self.assertEqual(PressRelease.objects.count(), 1)
        self.assertEqual(PressRelease.objects.first().id, first_id)

    def test_build_news_upserts_by_url(self):
        entry = {
            "id": "http://blog.scielo.org/?p=1",
            "title": "Title",
            "summary": "Summary",
            "published": "Wed, 29 Jan 2020 17:45:29 +0000",
        }
        news = controllers.build_news(entry, "en")
        news.save()
        first_id = news._id

        entry["title"] = "Updated"
        updated = controllers.build_news(entry, "en")
        updated.save()

        self.assertEqual(News.objects.count(), 1)
        self.assertEqual(News.objects.first()._id, first_id)
        self.assertEqual(News.objects.first().title, "Updated")

    def test_news_exists_by_url(self):
        self.assertFalse(controllers.news_exists_by_url("http://example.com/missing"))
        News(
            _id=str(uuid4().hex),
            title="One",
            description="d",
            url="http://example.com/1",
            language="pt",
            is_public=True,
            publication_date=datetime.datetime(2024, 3, 1),
        ).save()
        self.assertTrue(controllers.news_exists_by_url("http://example.com/1"))
        self.assertFalse(controllers.news_exists_by_url(""))

    def test_get_latest_news_by_lang(self):
        News(
            _id=str(uuid4().hex),
            title="One",
            description="d",
            url="http://example.com/1",
            language="pt",
            is_public=True,
            publication_date=datetime.datetime(2024, 3, 1),
        ).save()
        News(
            _id=str(uuid4().hex),
            title="Two",
            description="d",
            url="http://example.com/2",
            language="pt",
            is_public=True,
            publication_date=datetime.datetime(2024, 4, 1),
        ).save()
        latest = list(controllers.get_latest_news_by_lang("pt"))
        self.assertEqual(latest[0].title, "Two")


class CountAndEmailCoverageTests(BaseTestCase):
    def test_count_elements_news_sponsor_pressrelease(self):
        News(
            _id=str(uuid4().hex),
            title="N",
            description="d",
            url="http://example.com",
            language="pt",
            is_public=True,
            publication_date=datetime.datetime(2024, 1, 1),
        ).save()
        utils.makeOneSponsor()
        journal = utils.makeOneJournal()
        issue = utils.makeOneIssue({"journal": journal})
        PressRelease(
            _id=str(uuid4().hex),
            title="PR",
            language="pt",
            content="<p>x</p>",
            journal=journal.id,
            issue=issue.id,
            url="http://example.com/pr",
            publication_date=datetime.datetime(2024, 1, 1),
        ).save()
        self.assertEqual(controllers.count_elements_by_type_and_visibility("news"), 1)
        self.assertEqual(controllers.count_elements_by_type_and_visibility("sponsor"), 1)
        self.assertEqual(
            controllers.count_elements_by_type_and_visibility("pressrelease"), 1
        )

    @patch("webapp.controllers.utils.send_email", return_value=(True, "ok"))
    def test_send_email_share_success(self, mock_send):
        sent, message = controllers.send_email_share(
            "user@test.com", ["dest@test.com"], "http://example.com", None, "comment"
        )
        self.assertTrue(sent)
        self.assertEqual(message, __("Mensagem enviada!"))

    @patch("webapp.controllers.utils.send_email", return_value=(False, "fail"))
    def test_send_email_share_failure(self, mock_send):
        sent, message = controllers.send_email_share(
            "user@test.com", ["dest@test.com"], "http://example.com", "Subject", "comment"
        )
        self.assertFalse(sent)

    @patch("webapp.controllers.utils.send_email", return_value=(True, "ok"))
    def test_send_email_error_success(self, mock_send):
        for error_type in ("application", "content", "acessibility"):
            sent, message = controllers.send_email_error(
                "User",
                "user@test.com",
                ["dest@test.com"],
                "http://example.com/page",
                error_type,
                "details",
                "Page title",
            )
            self.assertTrue(sent)
            self.assertEqual(message, __("Mensagem enviada!"))

    @patch("webapp.controllers.utils.send_email", return_value=(False, "fail"))
    def test_send_email_error_failure(self, mock_send):
        sent, message = controllers.send_email_error(
            "User",
            "user@test.com",
            ["dest@test.com"],
            "http://example.com/page",
            "content",
            "details",
            "Page title",
        )
        self.assertFalse(sent)

    @patch("webapp.controllers.utils.send_email", return_value=(True, "ok"))
    def test_send_email_contact_success(self, mock_send):
        sent, message = controllers.send_email_contact(
            ["dest@test.com"], " Name ", " user@test.com ", "Hello"
        )
        self.assertTrue(sent)
        self.assertEqual(message, __("Mensagem enviada!"))

    @patch("webapp.controllers.utils.send_email", return_value=(False, "fail"))
    def test_send_email_contact_failure(self, mock_send):
        sent, message = controllers.send_email_contact(
            ["dest@test.com"], "Name", "user@test.com", "Hello"
        )
        self.assertFalse(sent)


class PagesAndRelatedCoverageTests(BaseTestCase):
    def test_get_page_by_journal_acron_lang(self):
        page = utils.makeOnePage({"journal": "abc", "language": "pt_BR"})
        result = controllers.get_page_by_journal_acron_lang("abc", "pt_BR")
        self.assertEqual(result.id, page.id)

    def test_get_page_by_id(self):
        page = utils.makeOnePage()
        result = controllers.get_page_by_id(page.id)
        self.assertEqual(result.id, page.id)

    def test_get_pages_by_lang_and_get_pages(self):
        page = utils.makeOnePage({"language": "en_US"})
        self.assertEqual(controllers.get_pages_by_lang("en_US").count(), 1)
        self.assertGreaterEqual(controllers.get_pages().count(), 1)
        self.assertEqual(page.id, controllers.get_pages().first().id)

    def test_get_page_by_slug_name_requires_slug(self):
        with self.assertRaises(ValueError):
            controllers.get_page_by_slug_name("")

    def test_get_page_by_slug_name_without_lang_returns_queryset(self):
        page = utils.makeOnePage({"name": "About Page"})
        results = controllers.get_page_by_slug_name(page.slug_name)
        self.assertEqual(results.count(), 1)

    def test_related_links_builds_search_expression(self):
        journal = utils.makeOneJournal({"title": "Journal Title"})
        issue = utils.makeOneIssue({"journal": journal})
        article = utils.makeOneArticle(
            {
                "journal": journal,
                "issue": issue,
                "title": "Article Title",
                "authors": ["Author One"],
                "publication_date": "2020-05-01",
                "section": "Research",
            }
        )
        links = controllers.related_links(article)
        self.assertEqual(len(links), 2)
        self.assertIn("Google", links[0][0])

    def test_related_links_with_minimal_article(self):
        journal = utils.makeOneJournal({"title": ""})
        issue = utils.makeOneIssue({"journal": journal})
        article = utils.makeOneArticle(
            {
                "journal": journal,
                "issue": issue,
                "title": "",
                "section": "",
                "authors": [],
                "publication_date": None,
            }
        )
        links = controllers.related_links(article)
        self.assertEqual(len(links), 2)

    def test_get_aop_issues_returns_ahead_issues(self):
        journal = utils.makeOneJournal()
        ahead = utils.makeOneIssue(
            {"journal": journal, "type": "ahead", "is_public": True, "year": 2023}
        )
        results = list(controllers.get_aop_issues(journal.url_segment))
        self.assertEqual(results[0].id, ahead.id)

    def test_get_aop_issues_requires_url_seg(self):
        with self.assertRaises(ValueError) as exc:
            controllers.get_aop_issues("")
        self.assertEqual(str(exc.exception), __("Obrigatório url_seg para get_aop_issues"))


class FactoryWrapperCoverageTests(BaseTestCase):
    def _load_fixture(self, filename):
        with open(os.path.join(FIXTURES_PATH, filename)) as handle:
            return json.load(handle)

    def test_add_journal_add_issue_and_add_article(self):
        journal_data = self._load_fixture("journal_payload.json")
        issue_data = self._load_fixture("issue_payload.json")
        article_data = self._load_fixture("article_payload.json")

        journal = controllers.add_journal(journal_data)
        self.assertEqual(journal.jid, journal_data["id"])

        issue = controllers.add_issue(issue_data, journal.jid)
        self.assertEqual(issue.iid, issue_data["id"])

        article = controllers.add_article(
            "article-coverage-id",
            article_data,
            issue.iid,
            1,
            "http://minio.scielo.org/documentstore/example.xml",
        )
        self.assertEqual(article.aid, "article-coverage-id")


class AddIssuePidUpsertTests(BaseTestCase):
    def _issue_payload(self, issue_id, pid, **overrides):
        data = {
            "id": issue_id,
            "publication_year": "2020",
            "volume": "1",
            "number": "1",
            "publication_months": {"range": [1, 3]},
            "pid": pid,
            "created": "2020-01-01T00:00:00.000000Z",
            "updated": "2020-01-02T00:00:00.000000Z",
        }
        data.update(overrides)
        return data

    def test_add_issue_updates_by_pid_when_id_changes_and_relinks_articles(self):
        journal = utils.makeOneJournal({"_id": "0000-pid-1"})
        pid = "0000pid120200002"
        old_id = "0000-pid-1-2020-v1-n1"
        new_id = "0000-pid-1-2020-v1"

        controllers.add_issue(self._issue_payload(old_id, pid), journal.jid)
        article = utils.makeOneArticle({"journal": journal, "issue": old_id})

        updated = controllers.add_issue(
            self._issue_payload(new_id, pid, number=None),
            journal.jid,
        )

        self.assertEqual(updated._id, new_id)
        self.assertEqual(updated.pid, pid)
        self.assertEqual(Issue.objects.filter(pid=pid).count(), 1)
        self.assertIsNone(Issue.objects.filter(_id=old_id).first())

        article.reload()
        self.assertEqual(article.issue.id, new_id)

    def test_add_issue_does_not_relink_articles_when_id_is_unchanged(self):
        journal = utils.makeOneJournal({"_id": "0000-pid-2"})
        pid = "0000pid220200002"
        issue_id = "0000-pid-2-2020-v1-n1"

        controllers.add_issue(self._issue_payload(issue_id, pid), journal.jid)
        article = utils.makeOneArticle({"journal": journal, "issue": issue_id})

        updated = controllers.add_issue(
            self._issue_payload(issue_id, pid, publication_year="2021"),
            journal.jid,
        )

        self.assertEqual(updated._id, issue_id)
        self.assertEqual(Issue.objects.count(), 1)
        article.reload()
        self.assertEqual(article.issue.id, issue_id)

    def test_add_issue_merges_duplicate_issues_with_same_pid(self):
        journal = utils.makeOneJournal({"_id": "0000-pid-3"})
        pid = "0000pid320200002"
        old_id = "0000-pid-3-2020-v1-n1"
        new_id = "0000-pid-3-2020-v1"

        old_issue = utils.makeOneIssue(
            {"_id": old_id, "journal": journal, "pid": pid, "number": "1"}
        )
        utils.makeOneIssue(
            {"_id": new_id, "journal": journal, "pid": pid, "number": None}
        )
        article = utils.makeOneArticle({"journal": journal, "issue": old_issue})

        updated = controllers.add_issue(
            self._issue_payload(new_id, pid, number=None),
            journal.jid,
        )

        self.assertEqual(updated._id, new_id)
        self.assertEqual(Issue.objects.filter(pid=pid).count(), 1)
        self.assertIsNone(Issue.objects.filter(_id=old_id).first())
        article.reload()
        self.assertEqual(article.issue.id, new_id)

    def test_add_issue_without_pid_creates_issue(self):
        journal = utils.makeOneJournal({"_id": "0000-pid-4"})
        issue_id = "0000-pid-4-2020-v1-n1"
        payload = self._issue_payload(issue_id, pid="")
        payload.pop("pid")

        created = controllers.add_issue(payload, journal.jid)

        self.assertEqual(created._id, issue_id)
        self.assertEqual(Issue.objects.count(), 1)

    def test_add_issue_creates_new_record_when_pid_is_unknown(self):
        journal = utils.makeOneJournal({"_id": "0000-pid-5"})
        utils.makeOneIssue(
            {
                "_id": "0000-pid-5-2020-v1-n1",
                "journal": journal,
                "pid": "0000pid520200001",
            }
        )

        created = controllers.add_issue(
            self._issue_payload("0000-pid-5-2020-v2-n1", "0000pid520200002"),
            journal.jid,
        )

        self.assertEqual(created._id, "0000-pid-5-2020-v2-n1")
        self.assertEqual(Issue.objects.count(), 2)

    def test_add_issue_relinks_press_release_and_last_issue_iid(self):
        old_id = "0000-pid-6-2020-v1-n1"
        new_id = "0000-pid-6-2020-v1"
        pid = "0000pid620200002"
        last_issue = utils.getLastIssue({"iid": old_id, "url_segment": "2020.v1n1"})
        journal = utils.makeOneJournal(
            {"_id": "0000-pid-6", "last_issue": last_issue}
        )
        controllers.add_issue(self._issue_payload(old_id, pid), journal.jid)
        article = utils.makeOneArticle({"journal": journal, "issue": old_id})
        press_release = PressRelease(
            _id=str(uuid4().hex),
            title="PR",
            language="pt",
            content="<p>content</p>",
            journal=journal.id,
            issue=old_id,
            article=article.id,
            url="http://example.com/pr",
            publication_date=datetime.datetime(2024, 1, 1),
        ).save()

        updated = controllers.add_issue(
            self._issue_payload(new_id, pid, number=None),
            journal.jid,
        )

        press_release.reload()
        journal.reload()
        self.assertEqual(press_release.issue.id, new_id)
        self.assertEqual(journal.last_issue.iid, updated.iid)
        self.assertEqual(Issue.objects.filter(_id=old_id).count(), 0)


class RemainingControllersCoverageTests(BaseTestCase):
    def test_get_journal_by_issn_returns_journal(self):
        journal = utils.makeOneJournal({"scielo_issn": "1234-5678"})
        result = controllers.get_journal_by_issn("1234-5678")
        self.assertEqual(result.id, journal.id)

    def test_set_last_issue_and_issue_count_returns_when_no_public_issues(self):
        journal = utils.makeOneJournal({"issue_count": None, "last_issue": None})
        result = controllers.set_last_issue_and_issue_count(journal)
        self.assertEqual(result.id, journal.id)

    def test_create_last_issue_for_journal_returns_none_without_url_segment_on_issue(self):
        journal = utils.makeOneJournal()
        issue = Mock()
        issue.url_segment = None
        self.assertIsNone(controllers.create_last_issue_for_journal(journal, issue))

    def test_journal_last_issues_yields_for_non_regular_last_issue_type(self):
        journal = utils.makeOneJournal()
        last_issue = utils.getLastIssue({"type": "ahead"})
        last_issue.url_segment = ""
        journal.last_issue = last_issue
        journal.save()
        issue = utils.makeOneIssue(
            {
                "journal": journal,
                "type": "regular",
                "year": 2020,
                "volume": "1",
                "number": "1",
            }
        )
        utils.makeOneArticle({"journal": journal, "issue": issue, "is_public": True})
        results = list(controllers.journal_last_issues())
        self.assertTrue(any(item["journal"] == journal.jid for item in results))

    def test_get_issue_by_pid_returns_issue(self):
        issue = utils.makeOneIssue({"pid": "issue-pid-123"})
        result = controllers.get_issue_by_pid("issue-pid-123")
        self.assertEqual(result.id, issue.id)

    def test_get_article_by_url_seg_returns_article(self):
        article = utils.makeOneArticle()
        result = controllers.get_article_by_url_seg(article.url_segment)
        self.assertEqual(result.id, article.id)

    def test_get_article_by_issue_article_seg_returns_article(self):
        issue = utils.makeOneIssue()
        article = utils.makeOneArticle({"issue": issue})
        result = controllers.get_article_by_issue_article_seg(
            issue.id, article.url_segment
        )
        self.assertEqual(result.id, article.id)

    def test_get_article_by_aop_url_segs_returns_article(self):
        journal = utils.makeOneJournal()
        issue = utils.makeOneIssue({"journal": journal})
        article = utils.makeOneArticle(
            {
                "journal": journal,
                "issue": issue,
                "aop_url_segs": {
                    "url_seg_issue": issue.url_segment,
                    "url_seg_article": "custom-aop-article",
                },
            }
        )
        article.aop_url_segs["url_seg_article"] = article.url_segment
        article.save()
        result = controllers.get_article_by_aop_url_segs(
            journal.id,
            issue.url_segment,
            article.url_segment,
        )
        self.assertEqual(result.id, article.id)

    def test_get_article_by_pid_v1_returns_article(self):
        article = utils.makeOneArticle(
            {"scielo_pids": {"v1": "PID-V1-TEST", "v2": "", "v3": "", "other": []}}
        )
        result = controllers.get_article_by_pid_v1("PID-V1-TEST")
        self.assertEqual(result.id, article.id)

    def test_get_article_by_pid_returns_article(self):
        article = utils.makeOneArticle({"pid": "PID-MAIN-TEST"})
        result = controllers.get_article_by_pid("PID-MAIN-TEST")
        self.assertEqual(result.id, article.id)

    def test_get_article_by_oap_pid_returns_article(self):
        article = utils.makeOneArticle({"aop_pid": "AOP-PID-TEST"})
        result = controllers.get_article_by_oap_pid("AOP-PID-TEST")
        self.assertEqual(result.id, article.id)

    @patch("webapp.controllers.PressRelease.objects")
    def test_create_press_release_record_reraises_exception(self, mock_objects):
        mock_objects.side_effect = RuntimeError("press release failed")
        with self.assertRaises(RuntimeError):
            controllers.create_press_release_record({"title": "x"})


class BranchCoverageTests(BaseTestCase):
    def test_get_press_release_without_article_filter(self):
        journal, issue, article = (
            utils.makeOneJournal(),
            None,
            None,
        )
        issue = utils.makeOneIssue({"journal": journal})
        PressRelease(
            _id=str(uuid4().hex),
            title="PR no article",
            language="pt",
            content="<p>x</p>",
            journal=journal.id,
            issue=issue.id,
            article=utils.makeOneArticle({"journal": journal, "issue": issue}).id,
            url="http://example.com/pr",
            publication_date=datetime.datetime(2024, 1, 1),
        ).save()
        result = controllers.get_press_release(journal, issue, "pt")
        self.assertEqual(result.title, "PR no article")

    def test_get_press_releases_with_explicit_query_filter(self):
        journal = utils.makeOneJournal()
        issue = utils.makeOneIssue({"journal": journal})
        PressRelease(
            _id=str(uuid4().hex),
            title="Filtered PR",
            language="en",
            content="<p>x</p>",
            journal=journal.id,
            issue=issue.id,
            url="http://example.com/pr",
            publication_date=datetime.datetime(2024, 1, 1),
        ).save()
        self.assertEqual(
            controllers.get_press_releases(query_filter={"language": "en"}).count(), 1
        )

    def test_set_last_issue_skips_when_issue_count_already_matches(self):
        journal = utils.makeOneJournal({"issue_count": 1, "last_issue": None})
        issue = utils.makeOneIssue(
            {
                "journal": journal,
                "type": "regular",
                "url_segment": "2020.v1n1",
                "year": 2020,
                "volume": "1",
                "number": "1",
            }
        )
        utils.makeOneArticle({"journal": journal, "issue": issue, "is_public": True})
        result = controllers.set_last_issue_and_issue_count(journal, issue, issue_count=1)
        self.assertEqual(result.issue_count, 1)

    def test_set_last_issue_skips_create_when_last_issue_complete(self):
        journal = utils.makeOneJournal(
            {
                "issue_count": None,
                "last_issue": utils.getLastIssue({"url_segment": "existing-seg"}),
            }
        )
        issue = utils.makeOneIssue(
            {
                "journal": journal,
                "type": "regular",
                "year": 2020,
                "volume": "1",
                "number": "1",
            }
        )
        utils.makeOneArticle({"journal": journal, "issue": issue, "is_public": True})
        journal.last_issue.url_segment = "existing-seg"
        journal.save()
        controllers.set_last_issue_and_issue_count(journal, issue)
        self.assertEqual(journal.last_issue.url_segment, "existing-seg")

    def test_journal_last_issues_skips_update_when_last_issue_present(self):
        journal = utils.makeOneJournal()
        last_issue = utils.getLastIssue({"type": "ahead"})
        last_issue.url_segment = "ready-seg"
        journal.last_issue = last_issue
        journal.save()
        results = list(controllers.journal_last_issues())
        self.assertEqual(
            results, [{"journal": journal.jid, "last_issue": "ready-seg"}]
        )

    def test_get_article_by_aid_without_journal_url_seg(self):
        journal = utils.makeOneJournal({"is_public": True})
        issue = utils.makeOneIssue({"journal": journal, "is_public": True})
        article = utils.makeOneArticle({"journal": journal, "issue": issue})
        result = controllers.get_article_by_aid(article.id)
        self.assertEqual(result.id, article.id)

    def test_get_existing_lang_keeps_requested_language(self):
        article = utils.makeOneArticle({"languages": ["pt", "en"]})
        self.assertEqual(controllers.get_existing_lang(article, "en", False), "en")

    def test_get_article_by_pdf_filename_returns_none_when_lang_prefix_mismatch(self):
        journal = utils.makeOneJournal({"acronym": "jsp"})
        issue = utils.makeOneIssue({"journal": journal, "label": "v1n1"})
        utils.makeOneArticle(
            {
                "journal": journal,
                "issue": issue,
                "pdfs": [
                    {
                        "lang": "pt",
                        "filename": "article.pdf",
                        "url": "http://example.com/pt.pdf",
                    }
                ],
            }
        )
        self.assertIsNone(
            controllers.get_article_by_pdf_filename("jsp", "v1n1", "en_article.pdf")
        )

    def test_get_article_by_suppl_material_filename_returns_none_when_missing(self):
        journal = utils.makeOneJournal({"acronym": "jsp"})
        issue = utils.makeOneIssue({"journal": journal, "label": "v1n1"})
        self.assertIsNone(
            controllers.get_article_by_suppl_material_filename(
                "jsp", "v1n1", "missing.pdf"
            )
        )

    def test_get_article_by_pdf_filename_returns_none_when_article_not_found(self):
        journal = utils.makeOneJournal({"acronym": "jsp"})
        utils.makeOneIssue({"journal": journal, "label": "v1n1"})
        self.assertIsNone(
            controllers.get_article_by_pdf_filename("jsp", "v1n1", "missing.pdf")
        )

    def test_journal_last_issues_yields_nothing_without_public_issues(self):
        utils.makeOneJournal()
        self.assertEqual(list(controllers.journal_last_issues()), [])

    def test_get_articles_by_date_range_journal_id_branch_only(self):
        journal = utils.makeOneJournal()
        issue = utils.makeOneIssue({"journal": journal})
        article = utils.makeOneArticle(
            {
                "journal": journal,
                "issue": issue,
                "updated": datetime.datetime(2024, 7, 10, 12, 0, 0),
            }
        )
        pagination = controllers.get_articles_by_date_range(
            datetime.datetime(2024, 7, 1),
            datetime.datetime(2024, 7, 31),
            journal_id=journal.id,
            journal_acronym=None,
        )
        self.assertEqual(pagination.items[0].id, article.id)

    def test_get_articles_by_date_range_without_journal_filter(self):
        article = utils.makeOneArticle(
            {"updated": datetime.datetime(2024, 8, 10, 12, 0, 0)}
        )
        pagination = controllers.get_articles_by_date_range(
            datetime.datetime(2024, 8, 1),
            datetime.datetime(2024, 8, 31),
        )
        self.assertEqual(pagination.items[0].id, article.id)

    @patch("webapp.controllers.utils.send_email", return_value=(True, "ok"))
    def test_send_email_error_application_type(self, mock_send):
        sent, message = controllers.send_email_error(
            "User",
            "user@test.com",
            ["dest@test.com"],
            "http://example.com/page",
            "application",
            "details",
            "Page title",
        )
        self.assertTrue(sent)

    @patch("webapp.controllers.utils.send_email", return_value=(True, "ok"))
    def test_send_email_error_content_type(self, mock_send):
        sent, message = controllers.send_email_error(
            "User",
            "user@test.com",
            ["dest@test.com"],
            "http://example.com/page",
            "content",
            "details",
            "Page title",
        )
        self.assertTrue(sent)

    @patch("webapp.controllers.utils.send_email", return_value=(True, "ok"))
    def test_send_email_error_acessibility_type(self, mock_send):
        sent, message = controllers.send_email_error(
            "User",
            "user@test.com",
            ["dest@test.com"],
            "http://example.com/page",
            "acessibility",
            "details",
            "Page title",
        )
        self.assertTrue(sent)

    @patch("webapp.controllers.utils.send_email", return_value=(True, "ok"))
    def test_send_email_error_unknown_type_defaults_to_content(self, mock_send):
        sent, message = controllers.send_email_error(
            "User",
            "user@test.com",
            ["dest@test.com"],
            "http://example.com/page",
            "unknown",
            "details",
            "Page title",
        )
        self.assertTrue(sent)
