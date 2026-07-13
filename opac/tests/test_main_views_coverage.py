# coding: utf-8
"""Targeted tests to reach full line+branch coverage of webapp.main.views."""

import json
import os
import tempfile
from contextlib import contextmanager
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

from flask import current_app, session, url_for
from opac_schema.v1.models import TranslatedSection
from webapp.main.views import (
    add_collection_to_g,
    get_lang_from_session,
    get_pdf_content,
    render_html,
    render_html_abstract,
    render_html_from_html,
    render_html_from_xml,
    remover_tags_html,
    use_ssm_url,
)
from webapp.utils import NonRetryableError, RetryableError

from . import utils
from .base import BaseTestCase
from .test_restapi import RestAPIAuthMixin


AJAX_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


class MainViewsCoverageMixin(object):
    def _make_article_bundle(self, article_attrib=None):
        utils.makeOneCollection()
        journal = utils.makeOneJournal()
        issue = utils.makeOneIssue({"journal": journal})
        article_data = {
            "title": "Article Y",
            "original_language": "en",
            "languages": ["en"],
            "issue": issue,
            "journal": journal,
            "url_segment": "10-11",
        }
        article_data.update(article_attrib or {})
        article = utils.makeOneArticle(article_data)
        return journal, issue, article


class BeforeRequestCoverageTests(MainViewsCoverageMixin, BaseTestCase):
    @patch("webapp.main.views.controllers.get_current_collection")
    def test_add_collection_to_g_handles_exception(self, mock_get_collection):
        mock_get_collection.side_effect = RuntimeError("db down")
        with current_app.test_request_context("/"):
            from flask import g

            if hasattr(g, "collection"):
                del g.collection
            add_collection_to_g()
            self.assertEqual(g.collection, {})

    def test_get_lang_from_session_without_session_key(self):
        with current_app.test_request_context("/"):
            session.clear()
            result = get_lang_from_session()
            self.assertEqual(result, current_app.config.get("BABEL_DEFAULT_LOCALE"))


class LocaleCoverageTests(BaseTestCase):
    def test_set_locale_appends_hash_to_referrer(self):
        with self.client as client:
            response = client.get(
                url_for("main.set_locale", lang_code="en"),
                query_string={"hash": "section-id"},
                headers={"Referer": "/about/"},
                follow_redirects=False,
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, "/about/#section-id")

    def test_set_locale_without_referrer_redirects_home(self):
        with self.client as client:
            response = client.get(
                url_for("main.set_locale", lang_code="en"),
                follow_redirects=False,
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, "/")


class IndexAndCollectionCoverageTests(MainViewsCoverageMixin, BaseTestCase):
    def test_index_updates_home_metrics_when_enabled(self):
        with current_app.app_context():
            utils.makeOneCollection()
            utils.makeOneJournal({"is_public": True, "current_status": "current"})
            utils.makeOneArticle({"is_public": True})
            previous = current_app.config["USE_HOME_METRICS"]
            current_app.config["USE_HOME_METRICS"] = True
            try:
                response = self.client.get(url_for("main.index"))
                self.assertStatus(response, 200)
            finally:
                current_app.config["USE_HOME_METRICS"] = previous

    def test_collection_list_resets_invalid_status_filter(self):
        with current_app.app_context():
            utils.makeOneCollection()
            response = self.client.get(
                url_for("main.collection_list"), query_string={"status": "invalid"}
            )
            self.assertStatus(response, 200)
            self.assertEqual(self.get_context_variable("query_filter"), "")

    def test_collection_list_thematic_resets_invalid_filters(self):
        with current_app.app_context():
            utils.makeOneCollection()
            response = self.client.get(
                url_for("main.collection_list_thematic"),
                query_string={"status": "bad", "filter": "bad"},
            )
            self.assertStatus(response, 200)
            self.assertEqual(self.get_context_variable("query_filter"), "")
            self.assertEqual(self.get_context_variable("filter"), "areas")

    def test_collection_list_feed_sets_last_issue_when_missing(self):
        with current_app.app_context():
            utils.makeOneCollection()
            journal = utils.makeOneJournal(
                {
                    "last_issue": utils.getLastIssue(
                        {"type": "ahead", "url_segment": None, "iid": "missing-iid"}
                    )
                }
            )
            issue = utils.makeOneIssue({"journal": journal, "type": "regular"})
            utils.makeOneArticle({"journal": journal, "issue": issue})
            response = self.client.get(url_for("main.collection_list_feed"))
            self.assertStatus(response, 200)


class RouterLegacyCoverageTests(MainViewsCoverageMixin, BaseTestCase):
    def test_sci_serial_unpublished_journal(self):
        with current_app.app_context():
            journal = utils.makeOneJournal(
                {
                    "is_public": False,
                    "unpublish_reason": "removed",
                    "print_issn": "1111-1111",
                }
            )
            response = self.client.get(
                url_for("main.router_legacy"),
                query_string={"script": "sci_serial", "pid": journal.print_issn},
            )
            self.assertStatus(response, 404)
            self.assertIn("removed", response.data.decode("utf-8"))

    def test_sci_serial_journal_not_found(self):
        with current_app.app_context():
            response = self.client.get(
                url_for("main.router_legacy"),
                query_string={"script": "sci_serial", "pid": "9999-9999"},
            )
            self.assertStatus(response, 404)

    def test_sci_issuetoc_unpublished_issue_and_journal(self):
        with current_app.app_context():
            journal = utils.makeOneJournal({"print_issn": "2222-2222"})
            issue = utils.makeOneIssue(
                {
                    "journal": journal,
                    "is_public": False,
                    "unpublish_reason": "issue hidden",
                }
            )
            response = self.client.get(
                url_for("main.router_legacy"),
                query_string={"script": "sci_issuetoc", "pid": issue.pid},
            )
            self.assertStatus(response, 404)
            self.assertIn("issue hidden", response.data.decode("utf-8"))

            issue.is_public = True
            issue.save()
            journal.is_public = False
            journal.unpublish_reason = "journal hidden"
            journal.save()
            response = self.client.get(
                url_for("main.router_legacy"),
                query_string={"script": "sci_issuetoc", "pid": issue.pid},
            )
            self.assertStatus(response, 404)
            self.assertIn("journal hidden", response.data.decode("utf-8"))

    def test_sci_issues_unpublished_journal(self):
        with current_app.app_context():
            journal = utils.makeOneJournal(
                {
                    "is_public": False,
                    "unpublish_reason": "closed",
                    "print_issn": "3333-3333",
                }
            )
            response = self.client.get(
                url_for("main.router_legacy"),
                query_string={"script": "sci_issues", "pid": journal.print_issn},
            )
            self.assertStatus(response, 404)

    def test_sci_issues_journal_not_found(self):
        with current_app.app_context():
            response = self.client.get(
                url_for("main.router_legacy"),
                query_string={"script": "sci_issues", "pid": "4444-4444"},
            )
            self.assertStatus(response, 404)

    @patch("webapp.main.views.controllers.get_article_by_pid_v2")
    def test_router_legacy_invalid_script_with_pid(self, mock_get_article):
        mock_get_article.return_value = Mock(journal=Mock(url_segment="x"), aid="a1")
        with current_app.app_context():
            response = self.client.get(
                url_for("main.router_legacy"),
                query_string={"script": "sci_unknown", "pid": "1111-11111111111111111"},
            )
            self.assertStatus(response, 400)

    @patch("webapp.main.views.controllers.get_article_by_pid_v2")
    def test_sci_pdf_redirects_to_article_detail_v3(self, mock_get_article):
        journal = utils.makeOneJournal()
        mock_get_article.return_value = Mock(
            journal=Mock(url_segment=journal.url_segment), aid="aid-pdf"
        )
        with current_app.app_context():
            response = self.client.get(
                url_for("main.router_legacy"),
                query_string={
                    "script": "sci_pdf",
                    "pid": "1111-11111111111111111",
                    "tlng": "en",
                },
                follow_redirects=False,
            )
            self.assertStatus(response, 301)
            self.assertIn("format=pdf", response.location)


class JournalCoverageTests(MainViewsCoverageMixin, BaseTestCase):
    def test_journal_detail_with_sections_and_recent_articles(self):
        with current_app.app_context():
            utils.makeOneCollection()
            journal = utils.makeOneJournal({"current_status": "current"})
            issue = utils.makeOneIssue({"journal": journal})
            utils.makeOneArticle({"journal": journal, "issue": issue})
            last_issue = utils.getLastIssue(
                {
                    "iid": issue.iid,
                    "sections": [
                        TranslatedSection(name="Articles", language="en"),
                        TranslatedSection(name="Artigos", language="pt"),
                    ],
                }
            )
            journal.last_issue = last_issue
            journal.save()
            response = self.client.get(
                url_for("main.journal_detail", url_seg=journal.url_segment)
            )
            self.assertStatus(response, 200)
            sections = self.get_context_variable("sections")
            self.assertEqual(len(sections), 1)
            self.assertEqual(sections[0].language, "en")

    @patch("webapp.main.views.utils.get_label_issue", return_value="")
    def test_journal_feed_without_last_issue(self, _mock_label):
        with current_app.app_context():
            utils.makeOneCollection()
            journal = utils.makeOneJournal({"last_issue": None})
            response = self.client.get(
                url_for("main.journal_feed", url_seg=journal.url_segment)
            )
            self.assertStatus(response, 200)

    def test_journal_feed_uses_original_language_when_session_lang_missing(self):
        with current_app.app_context():
            utils.makeOneCollection()
            journal = utils.makeOneJournal()
            issue = utils.makeOneIssue({"journal": journal})
            utils.makeOneArticle(
                {
                    "journal": journal,
                    "issue": issue,
                    "languages": ["en"],
                    "original_language": "en",
                }
            )
            with self.client.session_transaction() as sess:
                sess["lang"] = "pt_BR"
            response = self.client.get(
                url_for("main.journal_feed", url_seg=journal.url_segment)
            )
            self.assertStatus(response, 200)
            self.assertIn("lang=en", response.data.decode("utf-8"))


class AboutJournalCoverageTests(MainViewsCoverageMixin, BaseTestCase):
    @patch("webapp.main.views.utils.fetch_and_extract_section")
    @patch("webapp.main.views.controllers.get_page_by_journal_acron_lang")
    def test_about_journal_old_information_page_pt_fallback(
        self, mock_get_page, mock_fetch
    ):
        mock_get_page.return_value = None
        mock_fetch.return_value = "<p>about content</p>"
        with current_app.app_context():
            journal = utils.makeOneJournal({"old_information_page": True})
            with self.client.session_transaction() as sess:
                sess["lang"] = "pt_BR"
            response = self.client.get(
                url_for("main.about_journal", url_seg=journal.url_segment)
            )
            self.assertStatus(response, 200)
            self.assertIn("about content", response.data.decode("utf-8"))

    @patch("webapp.main.views.controllers.get_page_by_journal_acron_lang")
    def test_about_journal_old_information_page_es_fallback(self, mock_get_page):
        page = Mock(content="<p>contenido</p>")
        mock_get_page.side_effect = [None, page]
        with current_app.app_context():
            journal = utils.makeOneJournal({"old_information_page": True})
            with self.client.session_transaction() as sess:
                sess["lang"] = "es"
            response = self.client.get(
                url_for("main.about_journal", url_seg=journal.url_segment)
            )
            self.assertStatus(response, 200)

    @patch("webapp.main.views.controllers.get_page_by_journal_acron_lang")
    def test_about_journal_old_information_page_en_fallback(self, mock_get_page):
        page = Mock(content="<p>english</p>")
        mock_get_page.return_value = page
        with current_app.app_context():
            journal = utils.makeOneJournal({"old_information_page": True})
            with self.client.session_transaction() as sess:
                sess["lang"] = "en"
            response = self.client.get(
                url_for("main.about_journal", url_seg=journal.url_segment)
            )
            self.assertStatus(response, 200)


class JournalSearchAjaxCoverageTests(MainViewsCoverageMixin, BaseTestCase):
    def test_journals_search_alpha_ajax_requires_xhr(self):
        with current_app.app_context():
            response = self.client.get(url_for("main.journals_search_alpha_ajax"))
            self.assertStatus(response, 400)

    def test_journals_search_alpha_ajax_success(self):
        with current_app.app_context():
            utils.makeOneCollection()
            utils.makeOneJournal()
            response = self.client.get(
                url_for("main.journals_search_alpha_ajax"),
                headers=AJAX_HEADERS,
            )
            self.assertStatus(response, 200)

    def test_journals_search_by_theme_ajax_invalid_filter(self):
        with current_app.app_context():
            response = self.client.get(
                url_for("main.journals_search_by_theme_ajax"),
                query_string={"filter": "invalid"},
                headers=AJAX_HEADERS,
            )
            self.assertStatus(response, 200)
            data = response.get_json()
            self.assertEqual(data["error"], 401)

    def test_journals_search_by_theme_ajax_wos_and_publisher(self):
        with current_app.app_context():
            utils.makeOneCollection()
            utils.makeOneJournal({"study_areas": ["HEALTH SCIENCES"]})
            for filter_name in ("wos", "publisher"):
                response = self.client.get(
                    url_for("main.journals_search_by_theme_ajax"),
                    query_string={"filter": filter_name},
                    headers=AJAX_HEADERS,
                )
                self.assertStatus(response, 200)


class ContactAndEmailCoverageTests(MainViewsCoverageMixin, BaseTestCase):
    @contextmanager
    def _without_csrf(self):
        previous = current_app.config.get("WTF_CSRF_ENABLED")
        current_app.config["WTF_CSRF_ENABLED"] = False
        try:
            yield
        finally:
            if previous is None:
                current_app.config.pop("WTF_CSRF_ENABLED", None)
            else:
                current_app.config["WTF_CSRF_ENABLED"] = previous

    @patch("webapp.main.views.controllers.send_email_contact")
    @patch("webapp.main.views.utils.is_recaptcha_valid", return_value=True)
    def test_contact_ajax_success(self, _recaptcha, mock_send):
        mock_send.return_value = (True, "sent")
        with current_app.app_context():
            journal = utils.makeOneJournal({"enable_contact": True, "editor_email": "e@x.com"})
            with self._without_csrf():
                response = self.client.post(
                    url_for("main.contact", url_seg=journal.url_segment),
                    headers=AJAX_HEADERS,
                    data={
                        "name": "User",
                        "your_email": "user@example.com",
                        "message": "Hello",
                    },
                )
            self.assertStatus(response, 200)
            self.assertTrue(response.get_json()["sent"])

    @patch("webapp.main.views.utils.is_recaptcha_valid", return_value=True)
    def test_contact_ajax_validation_error(self, _recaptcha):
        with current_app.app_context():
            journal = utils.makeOneJournal({"enable_contact": True})
            with self._without_csrf():
                response = self.client.post(
                    url_for("main.contact", url_seg=journal.url_segment),
                    headers=AJAX_HEADERS,
                    data={"name": "", "your_email": "bad", "message": ""},
                )
            self.assertStatus(response, 200)
            self.assertFalse(response.get_json()["sent"])

    @patch("webapp.main.views.utils.is_recaptcha_valid", return_value=False)
    def test_contact_ajax_invalid_captcha(self, _recaptcha):
        with current_app.app_context():
            journal = utils.makeOneJournal({"enable_contact": True})
            response = self.client.post(
                url_for("main.contact", url_seg=journal.url_segment),
                headers=AJAX_HEADERS,
                data={"name": "User", "your_email": "user@example.com", "message": "Hi"},
            )
            self.assertStatus(response, 400)

    def test_form_contact_renders_template(self):
        with current_app.app_context():
            journal = utils.makeOneJournal()
            response = self.client.get(
                url_for("main.form_contact", url_seg=journal.url_segment)
            )
            self.assertStatus(response, 200)
            self.assertTemplateUsed("journal/includes/contact_form.html")

    @patch("webapp.main.views.controllers.send_email_share")
    def test_email_share_ajax_success(self, mock_send):
        mock_send.return_value = (True, "ok")
        with current_app.app_context():
            with self._without_csrf():
                response = self.client.post(
                    url_for("main.email_share_ajax"),
                    headers=AJAX_HEADERS,
                    data={
                        "your_email": "sender@example.com",
                        "recipients": "one@example.com",
                        "share_url": "http://example.com/article",
                        "subject": "Read this",
                        "comment": "Nice article",
                    },
                )
            self.assertStatus(response, 200)
            self.assertTrue(response.get_json()["sent"])

    def test_email_share_ajax_validation_error(self):
        with current_app.app_context():
            with self._without_csrf():
                response = self.client.post(
                    url_for("main.email_share_ajax"),
                    headers=AJAX_HEADERS,
                    data={"your_email": "bad", "recipients": "bad", "share_url": "not-a-url"},
                )
            self.assertStatus(response, 200)
            self.assertFalse(response.get_json()["sent"])

    def test_email_form_renders(self):
        with current_app.app_context():
            response = self.client.get(
                url_for("main.email_form"), query_string={"url": "http://example.com"}
            )
            self.assertStatus(response, 200)

    @patch("webapp.main.views.controllers.send_email_error")
    def test_email_error_ajax_success(self, mock_send):
        mock_send.return_value = (True, "reported")
        with current_app.app_context():
            with self._without_csrf():
                response = self.client.post(
                    url_for("main.email_error_ajax"),
                    headers=AJAX_HEADERS,
                    data={
                        "name": "User",
                        "your_email": "user@example.com",
                        "error_type": "404",
                        "url": "http://example.com/missing",
                        "page_title": "Missing",
                        "message": "Broken link",
                    },
                )
            self.assertStatus(response, 200)
            self.assertTrue(response.get_json()["sent"])

    def test_error_form_renders(self):
        with current_app.app_context():
            response = self.client.get(
                url_for("main.error_form"), query_string={"url": "http://example.com"}
            )
            self.assertStatus(response, 200)


class IssueTocCoverageTests(MainViewsCoverageMixin, BaseTestCase):
    def test_issue_toc_section_filter_and_math_content(self):
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle(
                {
                    "section": "Editorial",
                    "title": "Title with <mml:math>x</mml:math>",
                    "abstracts": [{"language": "en", "text": "Abstract"}],
                    "abstract_languages": [],
                    "htmls": [{"lang": "en", "url": "http://example.com/a.html"}],
                    "pdfs": [{"lang": "en", "url": "http://example.com/a.pdf"}],
                }
            )
            current_app.config["FILTER_SECTION_ENABLE"] = True
            current_app.config["FILTER_SECTION_ENABLE_FOR_MIN_STUDY_AREAS"] = 1
            journal.study_areas = ["HEALTH SCIENCES", "BIOLOGY"]
            journal.save()
            response = self.client.post(
                url_for(
                    "main.issue_toc",
                    url_seg=journal.url_segment,
                    url_seg_issue=issue.url_segment,
                ),
                data={"section": "editorial"},
            )
            self.assertStatus(response, 200)
            self.assertTrue(self.get_context_variable("has_math_content"))

    def test_issue_feed_language_fallback(self):
        with current_app.app_context():
            journal, issue, _article = self._make_article_bundle(
                {
                    "languages": ["en"],
                    "original_language": "en",
                    "htmls": [{"lang": "en", "url": "http://example.com/a.html"}],
                }
            )
            with self.client.session_transaction() as sess:
                sess["lang"] = "pt_BR"
            response = self.client.get(
                url_for(
                    "main.issue_feed",
                    url_seg=journal.url_segment,
                    url_seg_issue=issue.url_segment,
                )
            )
            self.assertStatus(response, 200)

    def test_aop_toc_section_filter(self):
        with current_app.app_context():
            journal = utils.makeOneJournal()
            aop_issue = utils.makeOneIssue(
                {"journal": journal, "type": "ahead", "number": "ahead"}
            )
            utils.makeOneArticle(
                {
                    "journal": journal,
                    "issue": aop_issue,
                    "section": "Original",
                    "is_aop": True,
                }
            )
            response = self.client.get(
                url_for("main.aop_toc", url_seg=journal.url_segment),
                query_string={"section": "original"},
            )
            self.assertStatus(response, 200)


class ArticleDetailCoverageTests(MainViewsCoverageMixin, BaseTestCase):
    def test_article_detail_pid_falls_back_to_oap_pid(self):
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle(
                {"aop_pid": "S0102-311X2018000100102", "pid": "other-pid"}
            )
            response = self.client.get(
                url_for("main.article_detail_pid", pid=article.aop_pid),
                follow_redirects=False,
            )
            self.assertStatus(response, 302)

    def test_article_detail_redirect_with_lang_code(self):
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle()
            response = self.client.get(
                url_for(
                    "main.article_detail",
                    url_seg=journal.url_segment,
                    url_seg_issue=issue.url_segment,
                    url_seg_article=article.url_segment,
                    lang_code="en",
                ),
                follow_redirects=False,
            )
            self.assertStatus(response, 302)
            self.assertIn("lang=en", response.location)

    @patch("webapp.main.views.controllers.get_article")
    def test_article_detail_v3_error_handlers(self, mock_get_article):
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle()
            url = url_for(
                "main.article_detail_v3",
                url_seg=journal.url_segment,
                article_pid_v3=article.aid,
                lang="en",
            )
            cases = [
                (Exception("nav"), 404, "Artigo inexistente", {"part": "abstract"}),
                (Exception("nav"), 404, "Resumo inexistente", {"part": "abstract"}),
            ]
            from webapp import controllers

            for exc, status, fragment, extra in cases:
                if fragment == "Resumo inexistente":
                    mock_get_article.side_effect = controllers.PreviousOrNextArticleNotFoundError
                else:
                    mock_get_article.side_effect = controllers.PreviousOrNextArticleNotFoundError
                response = self.client.get(url_for(
                    "main.article_detail_v3",
                    url_seg=journal.url_segment,
                    article_pid_v3=article.aid,
                    lang="en",
                    **extra,
                ))
                self.assertStatus(response, status)

            mock_get_article.side_effect = controllers.ArticleNotFoundError("x")
            self.assertStatus(self.client.get(url), 404)

            mock_get_article.side_effect = controllers.ArticleLangNotFoundError
            self.assertStatus(self.client.get(url), 500)

            mock_get_article.side_effect = controllers.ArticleAbstractNotFoundError
            self.assertStatus(
                self.client.get(
                    url_for(
                        "main.article_detail_v3",
                        url_seg=journal.url_segment,
                        article_pid_v3=article.aid,
                        part="abstract",
                        lang="en",
                    )
                ),
                404,
            )

            mock_get_article.side_effect = controllers.ArticleIsNotPublishedError("hidden")
            self.assertStatus(self.client.get(url), 404)

            mock_get_article.side_effect = ValueError("bad value")
            self.assertStatus(self.client.get(url), 404)

    @patch("webapp.main.views.render_html")
    def test_article_detail_v3_pdf_citation_and_https(self, mock_render_html):
        mock_render_html.return_value = ("<p>html</p>", ["en"])
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle(
                {
                    "title": "<b>Title</b> with tags",
                    "pdfs": [{"lang": "en", "url": "http://example.com/a.pdf"}],
                }
            )
            previous = current_app.config["FORCE_USE_HTTPS_GOOGLE_TAGS"]
            current_app.config["FORCE_USE_HTTPS_GOOGLE_TAGS"] = True
            try:
                response = self.client.get(
                    url_for(
                        "main.article_detail_v3",
                        url_seg=journal.url_segment,
                        article_pid_v3=article.aid,
                        lang="en",
                    )
                )
                self.assertStatus(response, 200)
            finally:
                current_app.config["FORCE_USE_HTTPS_GOOGLE_TAGS"] = previous

    @patch("webapp.utils.utils.fetch_data")
    def test_article_detail_v3_pdf_xml_csl_and_invalid_format(self, mock_fetch):
        mock_fetch.return_value = b"%PDF-1.4"
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle(
                {
                    "pdfs": [{"lang": "en", "url": "http://example.com/a.pdf"}],
                    "xml": "http://example.com/a.xml",
                }
            )
            base = url_for(
                "main.article_detail_v3",
                url_seg=journal.url_segment,
                article_pid_v3=article.aid,
            )
            self.assertStatus(
                self.client.get(base, query_string={"format": "pdf", "lang": "en"}),
                200,
            )
            self.assertStatus(
                self.client.get(base, query_string={"format": "xml", "lang": "en"}),
                200,
            )
            response = self.client.get(
                base, query_string={"format": "csl", "lang": "en"}, follow_redirects=False
            )
            self.assertStatus(response, 301)
            self.assertStatus(
                self.client.get(base, query_string={"format": "txt", "lang": "en"}),
                400,
            )

    def test_article_detail_v3_pdf_not_found_branches(self):
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle({"pdfs": []})
            response = self.client.get(
                url_for(
                    "main.article_detail_v3",
                    url_seg=journal.url_segment,
                    article_pid_v3=article.aid,
                    format="pdf",
                    lang="en",
                )
            )
            self.assertStatus(response, 404)

            article.pdfs = [{"lang": "en"}, {"lang": "en"}]
            article.save()
            response = self.client.get(
                url_for(
                    "main.article_detail_v3",
                    url_seg=journal.url_segment,
                    article_pid_v3=article.aid,
                    format="pdf",
                    lang="en",
                )
            )
            self.assertStatus(response, 404)


class RenderHtmlCoverageTests(MainViewsCoverageMixin, BaseTestCase):
    @patch("webapp.main.views.utils.fetch_data")
    @patch("webapp.main.views.HTMLGenerator")
    def test_render_html_from_xml_without_ssm_rewrite(self, mock_generator, mock_fetch):
        mock_fetch.return_value = b"<article></article>"
        generator = mock_generator.parse.return_value
        generator.generate.return_value = "html"
        generator.languages = ["en"]
        with current_app.app_context():
            current_app.config["SSM_XML_URL_REWRITE"] = False
            current_app.config.pop("HTML_GENERATOR_VERSION", None)
            journal, issue, article = self._make_article_bundle(
                {"xml": "http://example.com/article.xml"}
            )
            html, langs = render_html_from_xml(article, "en")
            self.assertEqual(html, "html")
            self.assertEqual(langs, ["en"])

    @patch("webapp.main.views.utils.fetch_data")
    def test_render_html_from_html_and_abstract(self, mock_fetch):
        mock_fetch.return_value = b"<p>html body</p>"
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle(
                {
                    "xml": None,
                    "htmls": [{"lang": "en", "url": "http://example.com/a.html"}],
                    "abstracts": [{"language": "en", "text": "Abstract text"}],
                    "abstract_languages": ["en"],
                }
            )
            html, langs = render_html_from_html(article, "en")
            self.assertIn("html body", html)
            abstract, abs_langs = render_html_abstract(article, "en")
            self.assertEqual(abstract, "Abstract text")
            with self.assertRaises(ValueError):
                render_html_from_html(article, "es")
            empty_html, empty_langs = render_html(article, "en", gs_abstract=False)
            self.assertIn("html body", empty_html)
            abs_html, _ = render_html(article, "en", gs_abstract=True)
            self.assertEqual(abs_html, "Abstract text")

    def test_render_html_without_sources(self):
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle({"xml": None, "htmls": []})
            html, langs = render_html(article, "en")
            self.assertEqual(html, "")
            self.assertEqual(langs, [])

    def test_use_ssm_url_relative_path(self):
        with current_app.app_context():
            result = use_ssm_url("/relative/path.xml")
            self.assertTrue(result.endswith("/relative/path.xml"))

    def test_remover_tags_html(self):
        self.assertEqual(remover_tags_html("<b>Title</b>"), "Title")


class MediaProxyCoverageTests(BaseTestCase):
    @patch("webapp.main.views.utils.fetch_data")
    def test_get_pdf_content_and_ssm_proxy(self, mock_fetch):
        mock_fetch.return_value = b"binary"
        with current_app.app_context():
            response = get_pdf_content("http://example.com/file.pdf")
            self.assertEqual(response.status_code, 200)
            response = self.client.get(
                url_for("main.media_assets_proxy", relative_media_path="img/logo.png")
            )
            self.assertStatus(response, 200)
            response = self.client.get(
                url_for(
                    "main.article_ssm_content_raw",
                    resource_ssm_path="/media/raw/content.html",
                )
            )
            self.assertStatus(response, 200)

    @patch("webapp.main.views.utils.fetch_data", side_effect=NonRetryableError)
    def test_get_pdf_content_not_found(self, _mock_fetch):
        with current_app.app_context():
            with self.assertRaises(Exception):
                get_pdf_content("http://example.com/missing.pdf")

    @patch("webapp.main.views.utils.fetch_data", side_effect=RetryableError)
    def test_get_pdf_content_retryable_error(self, _mock_fetch):
        with current_app.app_context():
            with self.assertRaises(Exception):
                get_pdf_content("http://example.com/retry.pdf")

    def test_article_ssm_content_raw_missing_path(self):
        with current_app.app_context():
            response = self.client.get(url_for("main.article_ssm_content_raw"))
            self.assertStatus(response, 404)


class EpdfAndLegacyPdfCoverageTests(MainViewsCoverageMixin, BaseTestCase):
    def test_article_epdf_requires_all_params(self):
        with current_app.app_context():
            response = self.client.get(url_for("main.article_epdf"))
            self.assertStatus(response, 400)

    def test_article_epdf_renders_template(self):
        with current_app.app_context():
            response = self.client.get(
                url_for("main.article_epdf"),
                query_string={
                    "doi": "10.1/test",
                    "pid": "pid",
                    "pdf_path": "/pdf/x.pdf",
                    "lang": "en",
                },
            )
            self.assertStatus(response, 200)
            self.assertTemplateUsed("article/epdf.html")

    def test_article_detail_pdf_redirect(self):
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle()
            response = self.client.get(
                url_for(
                    "main.article_detail_pdf",
                    url_seg=journal.url_segment,
                    url_seg_issue=issue.url_segment,
                    url_seg_article=article.url_segment,
                    lang_code="en",
                ),
                follow_redirects=False,
            )
            self.assertStatus(response, 301)

    def test_router_legacy_pdf_journal_not_found(self):
        with current_app.app_context():
            response = self.client.get(
                url_for(
                    "main.router_legacy_pdf",
                    journal_acron="missing",
                    issue_info="2020.v1",
                    pdf_filename="article",
                )
            )
            self.assertStatus(response, 404)

    def test_router_legacy_pdf_article_not_found(self):
        with current_app.app_context():
            journal = utils.makeOneJournal()
            response = self.client.get(
                url_for(
                    "main.router_legacy_pdf",
                    journal_acron=journal.url_segment,
                    issue_info="2020.v1",
                    pdf_filename="missing",
                )
            )
            self.assertStatus(response, 404)

    def test_router_legacy_article_invalid_request(self):
        with current_app.app_context():
            response = self.client.get(
                url_for("main.router_legacy_article", text_or_abstract="invalid")
            )
            self.assertStatus(response, 400)


class CitationCoverageTests(MainViewsCoverageMixin, BaseTestCase):
    def setUp(self):
        super().setUp()
        self._csl_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        self._csl_file.write(
            json.dumps(
                {
                    "data": [
                        {
                            "id": "apa",
                            "attributes": {
                                "title": "American Psychological Association",
                                "short_title": "APA",
                            },
                        }
                    ]
                }
            )
        )
        self._csl_file.close()

    def tearDown(self):
        os.unlink(self._csl_file.name)
        super().tearDown()

    @patch("webapp.main.views.render_template")
    @patch("webapp.main.views.utils.render_citation")
    def test_article_cite_csl_and_export(self, mock_render, mock_render_template):
        mock_render.return_value = ["Citation text"]
        mock_render_template.return_value = "TY  - JOUR\n"
        csl_payload = [{"id": "item", "type": "article-journal", "container-title": "Journal"}]
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle()
            with patch.object(
                type(article), "csl_json", MagicMock(return_value=csl_payload)
            ):
                response = self.client.get(
                    url_for("main.article_cite_csl", article_id=article.aid)
                )
                self.assertStatus(response, 200)
                response = self.client.get(
                    url_for("main.article_cite_csl", article_id=article.aid),
                    query_string={"csl": "true"},
                )
                self.assertStatus(response, 200)
                response = self.client.get(
                    url_for("main.article_cite_export_format", article_id=article.aid),
                    query_string={"format": "ris"},
                )
                self.assertStatus(response, 200)
                response = self.client.get(
                    url_for("main.article_cite_export_format", article_id=article.aid),
                    query_string={"format": "bib"},
                )
                self.assertStatus(response, 200)

    def test_article_cite_csl_list_search(self):
        with current_app.app_context():
            previous = current_app.config["COMMON_STYLE_LIST"]
            current_app.config["COMMON_STYLE_LIST"] = self._csl_file.name
            try:
                response = self.client.get(
                    url_for("main.article_cite_csl_list"), query_string={"q": "american"}
                )
                self.assertStatus(response, 200)
                data = response.get_json()
                self.assertGreaterEqual(len(data["results"]), 1)
            finally:
                current_app.config["COMMON_STYLE_LIST"] = previous

    def test_article_cite_export_invalid_format(self):
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle()
            response = self.client.get(
                url_for("main.article_cite_export_format", article_id=article.aid),
                query_string={"format": "invalid"},
            )
            self.assertStatus(response, 404)


class MiscRoutesCoverageTests(MainViewsCoverageMixin, BaseTestCase):
    def test_full_text_image_and_media_download(self):
        with current_app.app_context():
            response = self.client.get(url_for("main.full_text_image"))
            self.assertStatus(response, 200)

    @patch("webapp.main.views.send_from_directory")
    def test_download_file_by_filename(self, mock_send):
        mock_send.return_value = "ok"
        with current_app.app_context():
            response = self.client.get(url_for("main.download_file_by_filename", filename="x.png"))
            self.assertEqual(response.status_code, 200)

    def test_author_production_redirect_variants(self):
        with current_app.app_context():
            previous = current_app.config["URL_SEARCH"]
            for search_url in ("//search.scielo.org/", "http://search.scielo.org/", "search.scielo.org"):
                current_app.config["URL_SEARCH"] = search_url
                response = self.client.get(
                    "/cgi-bin/wxis.exe/iah/",
                    query_string={
                        "indexSearch": "AU",
                        "exprSearch": "Silva, João",
                        "lang": "p",
                    },
                    follow_redirects=False,
                )
                self.assertStatus(response, 301)
            current_app.config["URL_SEARCH"] = None
            response = self.client.get("/cgi-bin/wxis.exe/iah/")
            self.assertStatus(response, 404)
            current_app.config["URL_SEARCH"] = previous

    @patch("webapp.main.views.requests.get")
    def test_scimago_ir_returns_first_link(self, mock_get):
        mock_get.return_value = Mock(
            content=b"<a href='institution.php?idp=1'>Uni</a>"
        )
        with current_app.app_context():
            response = self.client.get(
                url_for("main.scimago_ir"),
                query_string={"q": "university"},
                headers=AJAX_HEADERS,
            )
            self.assertStatus(response, 200)
            self.assertIn("institution.php", response.get_data(as_text=True))

    @patch("webapp.main.views.requests.get")
    def test_scimago_ir_empty_result(self, mock_get):
        mock_get.return_value = Mock(content=b"<div>no results</div>")
        with current_app.app_context():
            response = self.client.get(
                url_for("main.scimago_ir"),
                query_string={"q": "missing"},
                headers=AJAX_HEADERS,
            )
            self.assertStatus(response, 200)
            self.assertEqual(response.get_data(as_text=True), "")


class RestApiViewsCoverageTests(RestAPIAuthMixin, BaseTestCase):
    def test_router_counter_dicts_default_pagination(self):
        with current_app.app_context():
            journal = utils.makeOneJournal()
            utils.makeOneArticle({"journal": journal})
            response = self.client.get(
                url_for("restapi.router_counter_dicts"),
                query_string={"page": "1", "limit": "200"},
            )
            self.assertStatus(response, 200)
            data = response.get_json()
            self.assertEqual(data["page"], 1)
            self.assertEqual(data["limit"], 100)
            response = self.client.get(
                url_for("restapi.router_counter_dicts"),
                query_string={"page": "1", "limit": "5"},
            )
            self.assertStatus(response, 200)
            self.assertEqual(response.get_json()["limit"], 5)

    def test_restapi_article_missing_article_url(self):
        with current_app.app_context():
            with self.client as client:
                response = self._api_post(
                    client,
                    "restapi.article",
                    {},
                    issue_id="issue-id",
                    article_id="article-id",
                    order=1,
                    follow_redirects=False,
                )
                self.assertStatus(response, 400)
                self.assertIn("missing param article_url", response.get_json()["error"])

    @patch("webapp.main.views.create_press_release_record")
    def test_restapi_pressrelease_success(self, mock_create):
        with current_app.app_context():
            journal = utils.makeOneJournal({"print_issn": "5555-5555"})
            payload = {
                "journal_id": journal.print_issn,
                "title": "Press",
                "language": "en",
                "doi": "10.1/pr",
                "content": "Body",
                "url": "http://example.com/pr",
                "media_content": "http://example.com/img.jpg",
                "publication_date": "2024-01-01",
            }
            with self.client as client:
                response = self._api_post(
                    client, "restapi.pressrelease", payload, follow_redirects=False
                )
                self.assertStatus(response, 200)
                mock_create.assert_called_once()

    def test_restapi_pressrelease_missing_journal_id(self):
        with current_app.app_context():
            with self.client as client:
                response = self._api_post(
                    client, "restapi.pressrelease", {"title": "x"}, follow_redirects=False
                )
                self.assertStatus(response, 200)
                self.assertTrue(response.get_json()["failed"])

    @patch("webapp.main.views.controllers.journal_last_issues")
    def test_restapi_journal_last_issues(self, mock_last_issues):
        mock_last_issues.return_value = [{"journal": "x"}]
        with current_app.app_context():
            with self.client as client:
                response = self._api_post(
                    client, "restapi.journal_last_issues", {}, follow_redirects=False
                )
                self.assertStatus(response, 200)
                self.assertEqual(response.get_json(), [{"journal": "x"}])


class RemainingMainViewsCoverageTests(MainViewsCoverageMixin, BaseTestCase):
    @patch("webapp.main.views.controllers.get_current_collection", side_effect=RuntimeError("db"))
    def test_before_request_collection_exception_via_client(self, _mock):
        with current_app.app_context():
            utils.makeOneCollection()
            response = self.client.get(url_for("main.index"))
            self.assertStatus(response, 200)

    def test_collection_list_feed_triggers_set_last_issue(self):
        with current_app.app_context():
            utils.makeOneCollection()
            journal = utils.makeOneJournal(
                {
                    "last_issue": utils.getLastIssue(
                        {"type": "ahead", "url_segment": "", "iid": "x"}
                    )
                }
            )
            issue = utils.makeOneIssue({"journal": journal, "type": "regular"})
            utils.makeOneArticle({"journal": journal, "issue": issue})
            response = self.client.get(url_for("main.collection_list_feed"))
            self.assertStatus(response, 200)

    def test_sci_issuetoc_issue_not_found_and_ahead_redirect(self):
        with current_app.app_context():
            journal = utils.makeOneJournal()
            ahead_issue = utils.makeOneIssue(
                {
                    "journal": journal,
                    "url_segment": "2020.ahead",
                    "type": "ahead",
                    "number": "ahead",
                }
            )
            response = self.client.get(
                url_for("main.router_legacy"),
                query_string={"script": "sci_issuetoc", "pid": "missing-pid"},
            )
            self.assertStatus(response, 404)
            response = self.client.get(
                url_for("main.router_legacy"),
                query_string={"script": "sci_issuetoc", "pid": ahead_issue.pid},
                follow_redirects=False,
            )
            self.assertStatus(response, 301)
            self.assertIn("aop", response.location)

    def test_journal_feed_triggers_set_last_issue(self):
        with current_app.app_context():
            utils.makeOneCollection()
            journal = utils.makeOneJournal(
                {
                    "last_issue": utils.getLastIssue(
                        {"type": "ahead", "url_segment": None, "iid": "feed-iid"}
                    )
                }
            )
            issue = utils.makeOneIssue({"journal": journal})
            utils.makeOneArticle({"journal": journal, "issue": issue})
            response = self.client.get(
                url_for("main.journal_feed", url_seg=journal.url_segment)
            )
            self.assertStatus(response, 200)

    @patch("webapp.main.views.utils.fetch_and_extract_section", return_value="about")
    def test_about_journal_unpublished_and_without_latest_issue(self, _mock_fetch):
        with current_app.app_context():
            from webapp import cache

            cache.clear()
            utils.makeOneCollection()
            journal = utils.makeOneJournal(
                {
                    "is_public": False,
                    "unpublish_reason": "hidden",
                    "last_issue": None,
                    "acronym": "hidden-jrn",
                }
            )
            response = self.client.get(
                url_for("main.about_journal", url_seg=journal.url_segment)
            )
            self.assertStatus(response, 404)

            public_journal = utils.makeOneJournal(
                {"last_issue": None, "acronym": "public-jrn"}
            )
            response = self.client.get(
                url_for("main.about_journal", url_seg=public_journal.url_segment)
            )
            self.assertStatus(response, 200)
            self.assertIsNone(self.get_context_variable("latest_issue_legend"))

    @patch("webapp.main.views.controllers.get_page_by_journal_acron_lang")
    def test_about_journal_old_page_attribute_error(self, mock_get_page):
        mock_get_page.return_value = object()
        with current_app.app_context():
            journal = utils.makeOneJournal({"old_information_page": True})
            with patch(
                "webapp.main.views.utils.fetch_and_extract_section",
                return_value="fallback",
            ):
                response = self.client.get(
                    url_for("main.about_journal", url_seg=journal.url_segment)
                )
                self.assertStatus(response, 200)

    def test_journals_search_by_theme_ajax_requires_xhr(self):
        with current_app.app_context():
            response = self.client.get(url_for("main.journals_search_by_theme_ajax"))
            self.assertStatus(response, 400)

    @patch("webapp.main.views.utils.is_recaptcha_valid", return_value=True)
    def test_contact_requires_xhr_and_disabled_contact(self, _recaptcha):
        with current_app.app_context():
            journal = utils.makeOneJournal({"enable_contact": False})
            response = self.client.post(url_for("main.contact", url_seg=journal.url_segment))
            self.assertStatus(response, 403)
            with self._without_csrf():
                response = self.client.post(
                    url_for("main.contact", url_seg=journal.url_segment),
                    headers=AJAX_HEADERS,
                    data={
                        "name": "User",
                        "your_email": "user@example.com",
                        "message": "Hi",
                    },
                )
            self.assertStatus(response, 403)

    def test_form_contact_journal_not_found(self):
        with current_app.app_context():
            response = self.client.get(url_for("main.form_contact", url_seg="missing"))
            self.assertStatus(response, 404)

    @contextmanager
    def _without_csrf(self):
        previous = current_app.config.get("WTF_CSRF_ENABLED")
        current_app.config["WTF_CSRF_ENABLED"] = False
        try:
            yield
        finally:
            if previous is None:
                current_app.config.pop("WTF_CSRF_ENABLED", None)
            else:
                current_app.config["WTF_CSRF_ENABLED"] = previous

    def test_issue_toc_get_without_section_filter(self):
        with current_app.app_context():
            journal, issue, _article = self._make_article_bundle()
            response = self.client.get(
                url_for(
                    "main.issue_toc",
                    url_seg=journal.url_segment,
                    url_seg_issue=issue.url_segment,
                )
            )
            self.assertStatus(response, 200)
            self.assertEqual(self.get_context_variable("section_filter"), "")

    def test_aop_toc_unpublished_journal(self):
        with current_app.app_context():
            journal = utils.makeOneJournal(
                {"is_public": False, "unpublish_reason": "closed"}
            )
            aop_issue = utils.makeOneIssue(
                {"journal": journal, "type": "ahead", "number": "ahead"}
            )
            utils.makeOneArticle({"journal": journal, "issue": aop_issue, "is_aop": True})
            response = self.client.get(url_for("main.aop_toc", url_seg=journal.url_segment))
            self.assertStatus(response, 404)

    def test_issue_feed_keeps_session_language_when_present(self):
        with current_app.app_context():
            journal, issue, _article = self._make_article_bundle(
                {"languages": ["en"], "original_language": "en"}
            )
            with self.client.session_transaction() as sess:
                sess["lang"] = "en"
            response = self.client.get(
                url_for(
                    "main.issue_feed",
                    url_seg=journal.url_segment,
                    url_seg_issue=issue.url_segment,
                )
            )
            self.assertStatus(response, 200)
            self.assertIn("lang=en", response.data.decode("utf-8"))

    def test_article_detail_pid_not_found(self):
        with current_app.app_context():
            response = self.client.get(
                url_for("main.article_detail_pid", pid="S0102-311X2099999999999")
            )
            self.assertStatus(response, 404)

    def test_render_html_abstract_without_matching_language(self):
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle(
                {
                    "xml": None,
                    "htmls": [],
                    "abstracts": [{"language": "pt", "text": "Resumo"}],
                    "abstract_languages": ["pt"],
                }
            )
            text, langs = render_html_abstract(article, "en")
            self.assertEqual(text, "")
            self.assertEqual(langs, ["pt"])

    def test_article_detail_not_found_paths(self):
        with current_app.app_context():
            journal = utils.makeOneJournal()
            issue = utils.makeOneIssue({"journal": journal})
            response = self.client.get(
                url_for(
                    "main.article_detail",
                    url_seg=journal.url_segment,
                    url_seg_issue="missing-issue",
                    url_seg_article="missing-article",
                )
            )
            self.assertStatus(response, 404)

            response = self.client.get(
                url_for(
                    "main.article_detail",
                    url_seg=journal.url_segment,
                    url_seg_issue=issue.url_segment,
                    url_seg_article="missing-article",
                )
            )
            self.assertStatus(response, 404)

            article = utils.makeOneArticle({"journal": journal, "issue": issue})
            response = self.client.get(
                url_for(
                    "main.article_detail",
                    url_seg=journal.url_segment,
                    url_seg_issue=issue.url_segment,
                    url_seg_article=article.url_segment,
                    lang_code="en",
                ),
                follow_redirects=False,
            )
            self.assertStatus(response, 302)

    @patch("webapp.main.views.controllers.get_article")
    def test_article_detail_v3_lang_not_found_and_abstract_nav_error(self, mock_get_article):
        from webapp import controllers

        with current_app.app_context():
            journal, issue, article = self._make_article_bundle(
                {"original_language": "", "languages": []}
            )
            article.original_language = ""
            article.languages = []
            article.save()
            mock_get_article.return_value = (None, article, {})
            response = self.client.get(
                url_for(
                    "main.article_detail_v3",
                    url_seg=journal.url_segment,
                    article_pid_v3=article.aid,
                    lang="en",
                )
            )
            self.assertStatus(response, 500)

            article.original_language = "en"
            article.save()
            mock_get_article.side_effect = controllers.PreviousOrNextArticleNotFoundError
            response = self.client.get(
                url_for(
                    "main.article_detail_v3",
                    url_seg=journal.url_segment,
                    article_pid_v3=article.aid,
                    part="abstract",
                    lang="en",
                )
            )
            self.assertStatus(response, 404)

    @patch("webapp.main.views.render_html", return_value=("<p>html</p>", ["en"]))
    def test_article_detail_v3_without_pdf_meta(self, _mock_render):
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle({"pdfs": []})
            response = self.client.get(
                url_for(
                    "main.article_detail_v3",
                    url_seg=journal.url_segment,
                    article_pid_v3=article.aid,
                    lang="en",
                )
            )
            self.assertStatus(response, 200)

    @patch("webapp.utils.utils.fetch_data", return_value=b"%PDF")
    def test_article_detail_v3_pdf_and_xml_branches(self, mock_fetch):
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle(
                {
                    "pdfs": [{"lang": "en"}],
                    "xml": "/relative/article.xml",
                }
            )
            response = self.client.get(
                url_for(
                    "main.article_detail_v3",
                    url_seg=journal.url_segment,
                    article_pid_v3=article.aid,
                    format="pdf",
                    lang="en",
                )
            )
            self.assertStatus(response, 404)

            current_app.config["SSM_XML_URL_REWRITE"] = False
            response = self.client.get(
                url_for(
                    "main.article_detail_v3",
                    url_seg=journal.url_segment,
                    article_pid_v3=article.aid,
                    format="xml",
                    lang="en",
                )
            )
            self.assertStatus(response, 200)

    @patch("webapp.main.views.utils.fetch_data")
    def test_get_pdf_content_ssm_rewrite_and_proxy_errors(self, mock_fetch):
        with current_app.app_context():
            current_app.config["SSM_ARTICLE_ASSETS_OR_RENDITIONS_URL_REWRITE"] = True
            mock_fetch.return_value = b"data"
            response = get_pdf_content("/relative/file.pdf")
            self.assertEqual(response.status_code, 200)

            mock_fetch.side_effect = NonRetryableError
            response = self.client.get(
                url_for("main.media_assets_proxy", relative_media_path="missing.png")
            )
            self.assertStatus(response, 404)

            mock_fetch.side_effect = RetryableError
            response = self.client.get(
                url_for(
                    "main.article_ssm_content_raw",
                    resource_ssm_path="/media/raw/content.html",
                )
            )
            self.assertStatus(response, 500)

    def test_article_detail_pdf_paths(self):
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle()
            response = self.client.get(
                url_for(
                    "main.article_detail_pdf",
                    url_seg=journal.url_segment,
                    url_seg_issue="2020v1",
                    url_seg_article="article",
                ),
                follow_redirects=False,
            )
            self.assertIn(response.status_code, (301, 404))

            response = self.client.get(
                url_for(
                    "main.article_detail_pdf",
                    url_seg=journal.url_segment,
                    url_seg_issue="missing",
                    url_seg_article="article",
                )
            )
            self.assertStatus(response, 404)

            response = self.client.get(
                url_for(
                    "main.article_detail_pdf",
                    url_seg=journal.url_segment,
                    url_seg_issue=issue.url_segment,
                    url_seg_article="missing",
                )
            )
            self.assertStatus(response, 404)

            response = self.client.get(
                url_for(
                    "main.article_detail_pdf",
                    url_seg=journal.url_segment,
                    url_seg_issue=issue.url_segment,
                    url_seg_article=article.url_segment,
                ),
                follow_redirects=False,
            )
            self.assertStatus(response, 301)

    @patch("webapp.main.views.controllers.get_article_by_pid", return_value=None)
    @patch("webapp.main.views.controllers.get_article_by_aid", return_value=None)
    def test_article_cite_not_found_and_short_title_search(
        self, _mock_aid, _mock_pid
    ):
        with current_app.app_context():
            response = self.client.get(
                url_for("main.article_cite_csl", article_id="missing-aid")
            )
            self.assertStatus(response, 404)

            response = self.client.get(
                url_for("main.article_cite_export_format", article_id="missing-aid"),
                query_string={"format": "ris"},
            )
            self.assertStatus(response, 404)

            csl_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            csl_file.write(
                json.dumps(
                    {
                        "data": [
                            {
                                "id": "apa",
                                "attributes": {
                                    "title": "Other Style",
                                    "short_title": "APA",
                                },
                            }
                        ]
                    }
                )
            )
            csl_file.close()
            previous = current_app.config["COMMON_STYLE_LIST"]
            current_app.config["COMMON_STYLE_LIST"] = csl_file.name
            try:
                response = self.client.get(
                    url_for("main.article_cite_csl_list"), query_string={"q": "apa"}
                )
                self.assertStatus(response, 200)
                self.assertEqual(len(response.get_json()["results"]), 1)
            finally:
                current_app.config["COMMON_STYLE_LIST"] = previous
                os.unlink(csl_file.name)

    def test_email_endpoints_require_xhr_and_validation_error(self):
        with current_app.app_context():
            response = self.client.post(url_for("main.email_share_ajax"))
            self.assertStatus(response, 400)
            response = self.client.post(url_for("main.email_error_ajax"))
            self.assertStatus(response, 400)
            with self._without_csrf():
                response = self.client.post(
                    url_for("main.email_error_ajax"),
                    headers=AJAX_HEADERS,
                    data={"name": "", "your_email": "bad"},
                )
            self.assertStatus(response, 200)
            self.assertFalse(response.get_json()["sent"])

    def test_scimago_ir_requires_xhr(self):
        with current_app.app_context():
            response = self.client.get(url_for("main.scimago_ir"))
            self.assertStatus(response, 400)


class FinalMainViewsCoverageTests(MainViewsCoverageMixin, BaseTestCase):
    def test_collection_and_journal_feed_with_valid_last_issue(self):
        with current_app.app_context():
            utils.makeOneCollection()
            journal = utils.makeOneJournal()
            issue = utils.makeOneIssue({"journal": journal, "type": "regular"})
            utils.makeOneArticle({"journal": journal, "issue": issue})
            last_issue = utils.getLastIssue(
                {
                    "iid": issue.iid,
                    "type": "regular",
                    "url_segment": issue.url_segment,
                }
            )
            journal.last_issue = last_issue
            journal.save()
            self.assertStatus(self.client.get(url_for("main.collection_list_feed")), 200)
            self.assertStatus(
                self.client.get(
                    url_for("main.journal_feed", url_seg=journal.url_segment)
                ),
                200,
            )

    def test_collection_and_journal_feed_refresh_last_issue_metadata(self):
        with current_app.app_context():
            utils.makeOneCollection()
            bad_last_issue = utils.getLastIssue(
                {"type": "special", "url_segment": "2020.v1", "iid": "bad-iid"}
            )
            journal = utils.makeOneJournal({"last_issue": bad_last_issue})
            issue = utils.makeOneIssue(
                {"journal": journal, "type": "regular", "iid": "good-iid"}
            )
            utils.makeOneArticle({"journal": journal, "issue": issue})
            journal.save()
            self.assertStatus(self.client.get(url_for("main.collection_list_feed")), 200)
            self.assertStatus(
                self.client.get(
                    url_for("main.journal_feed", url_seg=journal.url_segment)
                ),
                200,
            )

    @patch("webapp.main.views.utils.fetch_and_extract_section", return_value="fallback-about")
    def test_about_journal_without_old_information_page(self, _mock_fetch):
        with current_app.app_context():
            utils.makeOneCollection()
            journal = utils.makeOneJournal(
                {"old_information_page": False, "acronym": "modern-jrn"}
            )
            response = self.client.get(
                url_for("main.about_journal", url_seg=journal.url_segment)
            )
            self.assertStatus(response, 200)
            self.assertIn("fallback-about", response.data.decode("utf-8"))

    @patch("webapp.main.views.controllers.get_page_by_journal_acron_lang")
    def test_about_journal_old_page_finds_content(self, mock_get_page):
        mock_get_page.return_value = Mock(content="<p>English about</p>")
        with current_app.app_context():
            utils.makeOneCollection()
            journal = utils.makeOneJournal(
                {"old_information_page": True, "acronym": "about-jrn"}
            )
            response = self.client.get(
                url_for("main.about_journal", url_seg=journal.url_segment)
            )
            self.assertStatus(response, 200)
            self.assertIn("English about", response.data.decode("utf-8"))

    @patch("webapp.main.views.utils.fetch_and_extract_section", return_value="about")
    def test_about_journal_with_latest_issue_legend(self, _mock_fetch):
        with current_app.app_context():
            utils.makeOneCollection()
            journal = utils.makeOneJournal({"acronym": "legend-jrn"})
            issue = utils.makeOneIssue({"journal": journal})
            last_issue = utils.getLastIssue(
                {
                    "iid": issue.iid,
                    "year": issue.year,
                    "volume": issue.volume,
                    "number": issue.number,
                    "url_segment": issue.url_segment,
                }
            )
            journal.last_issue = last_issue
            journal.save()
            response = self.client.get(
                url_for("main.about_journal", url_seg=journal.url_segment)
            )
            self.assertStatus(response, 200)
            self.assertIsNotNone(self.get_context_variable("latest_issue_legend"))

    @patch("webapp.main.views.utils.fix_journal_last_issue", return_value=None)
    @patch("webapp.main.views.utils.fetch_and_extract_section", return_value="about")
    def test_about_journal_without_fixable_last_issue(self, _mock_fetch, _mock_fix):
        with current_app.app_context():
            utils.makeOneCollection()
            journal = utils.makeOneJournal(
                {"last_issue": None, "acronym": "no-issue-jrn"}
            )
            response = self.client.get(
                url_for("main.about_journal", url_seg=journal.url_segment)
            )
            self.assertStatus(response, 200)
            self.assertIsNone(self.get_context_variable("latest_issue_legend"))

    def test_journals_search_by_theme_ajax_areas_filter(self):
        with current_app.app_context():
            utils.makeOneCollection()
            utils.makeOneJournal({"study_areas": ["HEALTH SCIENCES"]})
            response = self.client.get(
                url_for("main.journals_search_by_theme_ajax"),
                query_string={"filter": "areas"},
                headers=AJAX_HEADERS,
            )
            self.assertStatus(response, 200)

    def test_issue_toc_section_filter_empty_post_value(self):
        with current_app.app_context():
            journal, issue, _article = self._make_article_bundle()
            response = self.client.post(
                url_for(
                    "main.issue_toc",
                    url_seg=journal.url_segment,
                    url_seg_issue=issue.url_segment,
                ),
                data={"section": ""},
            )
            self.assertStatus(response, 200)
            self.assertEqual(self.get_context_variable("section_filter"), "")

    @patch("webapp.main.views.controllers.get_aop_issues")
    def test_aop_toc_unpublished_journal_after_articles_collected(self, mock_aop):
        with current_app.app_context():
            journal = utils.makeOneJournal(
                {"is_public": False, "unpublish_reason": "closed", "acronym": "aop-jrn"}
            )
            aop_issue = utils.makeOneIssue(
                {
                    "journal": journal,
                    "type": "ahead",
                    "number": "ahead",
                    "is_public": True,
                    "url_segment": "2020.ahead",
                }
            )
            utils.makeOneArticle(
                {
                    "journal": journal,
                    "issue": aop_issue,
                    "is_aop": True,
                    "is_public": True,
                }
            )
            mock_aop.return_value = [aop_issue]
            response = self.client.get(url_for("main.aop_toc", url_seg=journal.url_segment))
            self.assertStatus(response, 404)

    @patch("webapp.main.views.controllers.get_article")
    def test_article_detail_v3_previous_next_error_on_full_text(self, mock_get_article):
        from webapp import controllers

        with current_app.app_context():
            journal, issue, article = self._make_article_bundle()
            mock_get_article.side_effect = controllers.PreviousOrNextArticleNotFoundError
            response = self.client.get(
                url_for(
                    "main.article_detail_v3",
                    url_seg=journal.url_segment,
                    article_pid_v3=article.aid,
                    lang="en",
                )
            )
            self.assertStatus(response, 404)

    @patch("webapp.main.views.render_html", return_value=("<p>html</p>", ["en"]))
    def test_article_detail_v3_https_citation_pdf_url(self, _mock_render):
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle(
                {"pdfs": [{"lang": "en", "url": "http://example.com/a.pdf"}]}
            )
            previous = current_app.config["FORCE_USE_HTTPS_GOOGLE_TAGS"]
            current_app.config["FORCE_USE_HTTPS_GOOGLE_TAGS"] = True
            try:
                response = self.client.get(
                    url_for(
                        "main.article_detail_v3",
                        url_seg=journal.url_segment,
                        article_pid_v3=article.aid,
                        lang="en",
                    )
                )
                self.assertStatus(response, 200)
                self.assertIn("https://", response.data.decode("utf-8"))
            finally:
                current_app.config["FORCE_USE_HTTPS_GOOGLE_TAGS"] = previous

    @patch("webapp.main.views.render_html", return_value=("<p>html</p>", ["en"]))
    def test_article_detail_v3_pdf_url_without_rewrite(self, _mock_render):
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle(
                {"pdfs": [{"lang": "en", "url": "http://example.com/a.pdf"}]}
            )
            current_app.config["FORCE_USE_HTTPS_GOOGLE_TAGS"] = False
            current_app.config["SSM_ARTICLE_ASSETS_OR_RENDITIONS_URL_REWRITE"] = False
            response = self.client.get(
                url_for(
                    "main.article_detail_v3",
                    url_seg=journal.url_segment,
                    article_pid_v3=article.aid,
                    lang="en",
                )
            )
            self.assertStatus(response, 200)

    @patch("webapp.utils.utils.fetch_data", return_value=b"%PDF")
    def test_article_detail_v3_pdf_empty_url_after_lookup(self, _mock_fetch):
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle(
                {"pdfs": [{"lang": "en", "url": ""}]}
            )
            response = self.client.get(
                url_for(
                    "main.article_detail_v3",
                    url_seg=journal.url_segment,
                    article_pid_v3=article.aid,
                    format="pdf",
                    lang="en",
                )
            )
            self.assertStatus(response, 404)

    def test_article_detail_pdf_issue_not_found(self):
        with current_app.app_context():
            journal = utils.makeOneJournal({"acronym": "pdf-jrn"})
            response = self.client.get(
                url_for(
                    "main.article_detail_pdf",
                    url_seg=journal.url_segment,
                    url_seg_issue="2020.v1n1",
                    url_seg_article="1-2",
                )
            )
            self.assertStatus(response, 404)

    def test_article_detail_redirect_without_lang_code(self):
        with current_app.app_context():
            journal, issue, article = self._make_article_bundle()
            response = self.client.get(
                url_for(
                    "main.article_detail",
                    url_seg=journal.url_segment,
                    url_seg_issue=issue.url_segment,
                    url_seg_article=article.url_segment,
                ),
                follow_redirects=False,
            )
            self.assertStatus(response, 302)
            self.assertNotIn("lang=", response.location)

    def test_article_cite_csl_list_without_query(self):
        with current_app.app_context():
            response = self.client.get(url_for("main.article_cite_csl_list"))
            self.assertStatus(response, 200)
            self.assertEqual(response.get_json()["results"], [])

    def test_article_cite_csl_list_no_match(self):
        csl_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        csl_file.write(
            json.dumps(
                {
                    "data": [
                        {
                            "id": "basic",
                            "attributes": {
                                "title": "Basic Citation Style",
                                "short_title": "BCS",
                            },
                        }
                    ]
                }
            )
        )
        csl_file.close()
        previous = current_app.config["COMMON_STYLE_LIST"]
        current_app.config["COMMON_STYLE_LIST"] = csl_file.name
        try:
            with current_app.app_context():
                response = self.client.get(
                    url_for("main.article_cite_csl_list"),
                    query_string={"q": "nomatch"},
                )
                self.assertStatus(response, 200)
                self.assertEqual(response.get_json()["results"], [])
        finally:
            current_app.config["COMMON_STYLE_LIST"] = previous
            os.unlink(csl_file.name)

    def test_article_cite_csl_list_without_short_title(self):
        csl_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        csl_file.write(
            json.dumps(
                {
                    "data": [
                        {
                            "id": "basic",
                            "attributes": {"title": "Basic Citation Style"},
                        }
                    ]
                }
            )
        )
        csl_file.close()
        previous = current_app.config["COMMON_STYLE_LIST"]
        current_app.config["COMMON_STYLE_LIST"] = csl_file.name
        try:
            with current_app.app_context():
                response = self.client.get(
                    url_for("main.article_cite_csl_list"),
                    query_string={"q": "basic"},
                )
                self.assertStatus(response, 200)
                self.assertEqual(len(response.get_json()["results"]), 1)
        finally:
            current_app.config["COMMON_STYLE_LIST"] = previous
            os.unlink(csl_file.name)

    def test_article_cite_csl_list_short_title_only_match(self):
        csl_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        csl_file.write(
            json.dumps(
                {
                    "data": [
                        {
                            "id": "ama",
                            "attributes": {
                                "title": "American Medical Association",
                                "short_title": "Other",
                            },
                        }
                    ]
                }
            )
        )
        csl_file.close()
        previous = current_app.config["COMMON_STYLE_LIST"]
        current_app.config["COMMON_STYLE_LIST"] = csl_file.name
        try:
            with current_app.app_context():
                response = self.client.get(
                    url_for("main.article_cite_csl_list"),
                    query_string={"q": "other"},
                )
                self.assertStatus(response, 200)
                self.assertEqual(len(response.get_json()["results"]), 1)
        finally:
            current_app.config["COMMON_STYLE_LIST"] = previous
            os.unlink(csl_file.name)

    def test_article_cite_csl_list_title_term_match(self):
        csl_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        csl_file.write(
            json.dumps(
                {
                    "data": [
                        {
                            "id": "ama",
                            "attributes": {
                                "title": "American Medical Association",
                                "short_title": "Other",
                            },
                        }
                    ]
                }
            )
        )
        csl_file.close()
        previous = current_app.config["COMMON_STYLE_LIST"]
        current_app.config["COMMON_STYLE_LIST"] = csl_file.name
        try:
            with current_app.app_context():
                response = self.client.get(
                    url_for("main.article_cite_csl_list"),
                    query_string={"q": "medical"},
                )
                self.assertStatus(response, 200)
                self.assertEqual(len(response.get_json()["results"]), 1)
        finally:
            current_app.config["COMMON_STYLE_LIST"] = previous
            os.unlink(csl_file.name)


class RestApiViewsCoverageTestsExtra(RestAPIAuthMixin, BaseTestCase):
    def test_restapi_article_add_failure(self):
        with current_app.app_context():
            with self.client as client:
                with patch(
                    "webapp.main.views.controllers.add_article",
                    side_effect=RuntimeError("boom"),
                ):
                    response = self._api_post(
                        client,
                        "restapi.article",
                        {"id": "x"},
                        issue_id="issue-id",
                        article_id="article-id",
                        order=1,
                        article_url="http://example.com/article.xml",
                        follow_redirects=False,
                    )
                self.assertStatus(response, 500)
                self.assertTrue(response.get_json()["failed"])

    @patch("webapp.main.views.create_press_release_record", side_effect=RuntimeError("fail"))
    def test_restapi_pressrelease_failure(self, _mock_create):
        with current_app.app_context():
            journal = utils.makeOneJournal({"print_issn": "6666-6666"})
            payload = {
                "journal_id": journal.print_issn,
                "title": "Press",
                "language": "en",
            }
            with self.client as client:
                response = self._api_post(
                    client, "restapi.pressrelease", payload, follow_redirects=False
                )
                self.assertStatus(response, 500)
                self.assertTrue(response.get_json()["failed"])


class LegacyInfoPagesCoverageTests(BaseTestCase):
    def test_router_legacy_info_pages_with_known_anchor(self):
        utils.makeOneCollection()
        journal = utils.makeOneJournal({"url_segment": "acron_ia"})
        response = self.client.get(
            "/revistas/%s/iaboutj.htm" % journal.url_segment,
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 301)
        self.assertIn("/about/", response.location)
        self.assertIn("#about", response.location)

    def test_router_legacy_info_pages_without_anchor(self):
        utils.makeOneCollection()
        journal = utils.makeOneJournal({"url_segment": "acron_sub"})
        response = self.client.get(
            "/revistas/%s/isubscrp.htm" % journal.url_segment,
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 301)
        self.assertIn("/about/", response.location)
        self.assertNotIn("#", response.location)
