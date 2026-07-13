# coding: utf-8

import importlib
import os
import sys
import tempfile
from datetime import datetime, timezone
from io import open as io_open
from unittest.mock import Mock, patch

import pytz
import requests
import webapp
from flask import current_app
from PIL import Image
from webapp import models
from webapp.utils.utils import (
    NonRetryableError,
    RetryableError,
    _get_fetch_data_timeout,
    asbool,
    create_db_tables,
    create_user,
    create_file,
    create_image,
    create_new_journal_page,
    create_page,
    extract_section,
    fetch_and_extract_section,
    fetch_data,
    fix_journal_last_issue,
    get_next_article,
    get_prev_article,
    get_resource_url,
    get_resources_url,
    get_timed_serializer,
    get_label_issue,
    join_html_files_content,
    migrate_page_content,
    migrate_page_create_file,
    migrate_page_create_image,
    namegen_filename,
    normalize_lang_portuguese,
    open_file,
    render_citation,
    replace_link,
    reset_db,
    send_audit_log_daily_report,
    send_email,
    utc_to_local,
)

from . import utils as test_utils
from .base import BaseTestCase


class UtilsCoverageTestCase(BaseTestCase):
    def test_get_timed_serializer(self):
        serializer = get_timed_serializer()
        token = serializer.dumps("test@example.com", salt="test")
        self.assertEqual("test@example.com", serializer.loads(token, salt="test"))

    def test_get_label_issue(self):
        issue = test_utils.makeOneIssue(
            {"volume": "10", "number": "2", "year": "2020"}
        )
        self.assertEqual("Vol. 10 No. 2 - 2020", get_label_issue(issue))

        issue_no_volume = test_utils.makeOneIssue(
            {"volume": None, "number": "2", "year": "2020"}
        )
        self.assertEqual("No. 2 - 2020", get_label_issue(issue_no_volume))

    def test_get_prev_and_next_article_happy_path(self):
        article1 = test_utils.makeOneArticle({"order": "1"})
        article2 = test_utils.makeOneArticle({"order": "2"})
        articles = [article1, article2]
        self.assertEqual(article1, get_prev_article(articles, article2))
        self.assertEqual(article2, get_next_article(articles, article1))

    def test_migrate_page_content_with_empty_content(self):
        self.assertIsNone(migrate_page_content("", language="pt", acron="rbep"))

    @patch("webapp.utils.utils.create_page")
    @patch("webapp.utils.utils.migrate_page_content")
    @patch("webapp.utils.utils.join_html_files_content", return_value="")
    def test_create_new_journal_page_with_empty_content(
        self, mocked_join, mocked_migrate, mocked_create_page
    ):
        self.assertIsNone(create_new_journal_page("rbep", ["about.htm"], "pt"))
        mocked_migrate.assert_not_called()
        mocked_create_page.assert_not_called()

    def test_render_citation_warns_on_missing_reference(self):
        from webapp.utils.utils import CitationStylesBibliography

        csl_json = [
            {
                "id": "item1",
                "type": "article-journal",
                "title": "Sample Article",
                "author": [{"family": "Silva", "given": "João"}],
                "issued": {"date-parts": [[2020, 1]]},
            }
        ]
        real_cite = CitationStylesBibliography.cite

        def cite_and_warn(self, citation, warn_cb):
            warn_cb(Mock(key="missing-key"))
            return real_cite(self, citation, warn_cb)

        with patch.object(CitationStylesBibliography, "cite", cite_and_warn):
            with patch("builtins.print") as mocked_print:
                citations = render_citation(csl_json, style="apa")
        self.assertEqual(1, len(citations))
        mocked_print.assert_called()
        self.assertIn("missing-key", mocked_print.call_args[0][0])

    def test_replace_link_without_hash_unchanged(self):
        from bs4 import BeautifulSoup

        html = '<section><a href="http://example.com/page">link</a></section>'
        section = BeautifulSoup(html, "html.parser").find("section")
        result = replace_link(section)
        self.assertEqual("http://example.com/page", result.find("a")["href"])

    def test_create_image_without_existing_record(self):
        image_root = tempfile.mkdtemp()
        original_image_root = current_app.config["IMAGE_ROOT"]
        current_app.config["IMAGE_ROOT"] = image_root
        source = os.path.join(tempfile.gettempdir(), "unique_source.png")
        Image.new("RGB", (10, 10), color="yellow").save(source)
        try:
            result = create_image(
                source, "unique_new.png", thumbnail=False, check_if_exists=True
            )
            self.assertEqual("unique_new.png", result.name)
        finally:
            current_app.config["IMAGE_ROOT"] = original_image_root

    def test_create_file_without_existing_record(self):
        file_root = tempfile.mkdtemp()
        original_file_root = current_app.config["FILE_ROOT"]
        current_app.config["FILE_ROOT"] = file_root
        source = os.path.join(tempfile.gettempdir(), "unique_doc.txt")
        with io_open(source, "w", encoding="utf-8") as handle:
            handle.write("unique")
        try:
            result = create_file(source, "unique_new.txt", check_if_exists=True)
            self.assertEqual("unique_new.txt", result.name)
        finally:
            current_app.config["FILE_ROOT"] = original_file_root

        result = namegen_filename("my photo.jpg")
        self.assertEqual("my_photo.jpg", result)

    def test_namegen_filename_with_string(self):
        result = namegen_filename("my photo.jpg")
        self.assertEqual("my_photo.jpg", result)

    def test_namegen_filename_with_model_object(self):
        obj = Mock()
        obj.name = "cover image"
        file_data = Mock()
        file_data.filename = "cover image.png"
        result = namegen_filename(obj, file_data)
        self.assertEqual("cover_image.png", result)

    def test_open_file_success_and_io_error(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="iso-8859-1") as tmp:
            tmp.write("conteúdo")
            path = tmp.name

        try:
            with open_file(path, mode="r", encoding="iso-8859-1") as handle:
                self.assertEqual("conteúdo", handle.read())
        finally:
            os.unlink(path)

        with self.assertRaises(IOError):
            open_file("/path/that/does/not/exist.dat", mode="r", encoding="iso-8859-1")

    def test_get_prev_article_empty_list(self):
        self.assertIsNone(get_prev_article([], Mock()))

    def test_get_next_article_empty_list(self):
        self.assertIsNone(get_next_article([], Mock()))

    def test_get_prev_article_index_error(self):
        class FakeArticles(object):
            def __len__(self):
                return 1

            def index(self, article):
                return 999

            def __getitem__(self, idx):
                raise IndexError

        self.assertIsNone(get_prev_article(FakeArticles(), Mock()))

    def test_get_next_article_index_error(self):
        class FakeArticles(object):
            def __len__(self):
                return 3

            def index(self, article):
                return 3

            def __getitem__(self, idx):
                raise IndexError

        self.assertIsNone(get_next_article(FakeArticles(), Mock()))

    def test_get_next_article_when_index_equals_length(self):
        class FakeArticles(object):
            def __len__(self):
                return 2

            def index(self, article):
                return 2

        self.assertIsNone(get_next_article(FakeArticles(), Mock()))

    @patch("webapp.mail.send")
    def test_send_email_with_list_recipient(self, mocked_send):
        ok, err = send_email(["a@example.com", "b@example.com"], "subject", "<p>hi</p>")
        self.assertTrue(ok)
        self.assertEqual("", err)
        mocked_send.assert_called_once()
        msg = mocked_send.call_args[0][0]
        self.assertEqual(["a@example.com", "b@example.com"], msg.recipients)

    @patch("webapp.mail.send", side_effect=RuntimeError("smtp down"))
    def test_send_email_exception_returns_false(self, mocked_send):
        ok, err = send_email("a@example.com", "subject", "<p>hi</p>")
        self.assertFalse(ok)
        self.assertIsInstance(err, RuntimeError)
        mocked_send.assert_called_once()

    def test_reset_db(self):
        create_user("reset@test.com", "secret", True)
        self.assertEqual(1, models.User.query.count())
        reset_db()
        self.assertEqual(0, models.User.query.count())

    def test_create_db_tables_success(self):
        from sqlalchemy import inspect

        webapp.dbsql.drop_all()
        create_db_tables()
        self.assertTrue(inspect(webapp.dbsql.engine).has_table("user"))

    @patch.object(webapp.dbsql, "create_all", side_effect=RuntimeError("db fail"))
    def test_create_db_tables_raises_exception(self, mocked_create_all):
        with self.assertRaises(RuntimeError):
            create_db_tables()

    @patch("webapp.utils.utils.generate_thumbnail")
    def test_create_image_full_path_with_thumbnail_and_existing(self, mocked_thumb):
        image_root = tempfile.mkdtemp()
        file_root = tempfile.mkdtemp()
        original_image_root = current_app.config["IMAGE_ROOT"]
        current_app.config["IMAGE_ROOT"] = image_root

        source = os.path.join(tempfile.gettempdir(), "source.png")
        Image.new("RGB", (10, 10), color="blue").save(source)

        existing = models.Image(name="existing.png", path="images/existing.png")
        webapp.dbsql.session.add(existing)
        webapp.dbsql.session.commit()
        dest_name = "existing.png"

        try:
            result = create_image(
                source, dest_name, thumbnail=True, check_if_exists=True
            )
            self.assertEqual(existing.id, result.id)
            mocked_thumb.assert_called_once()
        finally:
            current_app.config["IMAGE_ROOT"] = original_image_root

    def test_create_image_creates_directory_and_new_record(self):
        image_root = tempfile.mkdtemp()
        nested_root = os.path.join(image_root, "nested")
        original_image_root = current_app.config["IMAGE_ROOT"]
        current_app.config["IMAGE_ROOT"] = nested_root

        source = os.path.join(tempfile.gettempdir(), "new_source.png")
        Image.new("RGB", (10, 10), color="green").save(source)

        try:
            result = create_image(
                source, "brand_new.png", thumbnail=False, check_if_exists=False
            )
            self.assertTrue(os.path.isdir(nested_root))
            self.assertEqual("brand_new.png", result.name)
            self.assertTrue(os.path.isfile(os.path.join(nested_root, "brand_new.png")))
        finally:
            current_app.config["IMAGE_ROOT"] = original_image_root

    @patch("webapp.utils.utils.shutil.copyfile", side_effect=IOError("copy failed"))
    def test_create_image_io_error(self, mocked_copy):
        image_root = tempfile.mkdtemp()
        original_image_root = current_app.config["IMAGE_ROOT"]
        current_app.config["IMAGE_ROOT"] = image_root
        try:
            self.assertIsNone(
                create_image("/missing/source.png", "x.png", check_if_exists=False)
            )
        finally:
            current_app.config["IMAGE_ROOT"] = original_image_root

    def test_create_file_full_path_with_existing(self):
        file_root = tempfile.mkdtemp()
        original_file_root = current_app.config["FILE_ROOT"]
        current_app.config["FILE_ROOT"] = file_root

        source = os.path.join(tempfile.gettempdir(), "doc.txt")
        with io_open(source, "w", encoding="utf-8") as handle:
            handle.write("file content")

        existing = models.File(name="doc.txt", path="files/doc.txt")
        webapp.dbsql.session.add(existing)
        webapp.dbsql.session.commit()

        try:
            result = create_file(source, "doc.txt", check_if_exists=True)
            self.assertEqual(existing.id, result.id)
        finally:
            current_app.config["FILE_ROOT"] = original_file_root

    def test_create_file_creates_directory_and_new_record(self):
        file_root = tempfile.mkdtemp()
        nested_root = os.path.join(file_root, "nested")
        original_file_root = current_app.config["FILE_ROOT"]
        current_app.config["FILE_ROOT"] = nested_root

        source = os.path.join(tempfile.gettempdir(), "new_doc.txt")
        with io_open(source, "w", encoding="utf-8") as handle:
            handle.write("new file")

        try:
            result = create_file(source, "new_doc.txt", check_if_exists=False)
            self.assertTrue(os.path.isdir(nested_root))
            self.assertEqual("new_doc.txt", result.name)
            self.assertTrue(os.path.isfile(os.path.join(nested_root, "new_doc.txt")))
        finally:
            current_app.config["FILE_ROOT"] = original_file_root

    @patch("webapp.utils.utils.shutil.copyfile", side_effect=IOError("copy failed"))
    def test_create_file_io_error(self, mocked_copy):
        file_root = tempfile.mkdtemp()
        original_file_root = current_app.config["FILE_ROOT"]
        current_app.config["FILE_ROOT"] = file_root
        try:
            self.assertIsNone(
                create_file("/missing/source.txt", "x.txt", check_if_exists=False)
            )
        finally:
            current_app.config["FILE_ROOT"] = original_file_root

    def test_create_page(self):
        page = create_page(
            name="About",
            language="pt",
            content="<p>content</p>",
            journal="rbep",
            description="desc",
        )
        self.assertEqual("About", page.name)
        self.assertEqual("rbep", page.journal)

    @patch("webapp.utils.journal_static_page.OldJournalPageFile")
    def test_join_html_files_content_with_unavailable_message(self, mocked_page_cls):
        unavailable_page = Mock()
        unavailable_page.unavailable_message = "<p>not available</p>"
        unavailable_page.anchor = "<a></a>"
        unavailable_page.anchor_title = "Title"
        unavailable_page.body = "<p>body</p>"

        available_page = Mock()
        available_page.unavailable_message = None
        available_page.body = "<p>available body</p>"

        mocked_page_cls.side_effect = [unavailable_page, available_page]
        content = join_html_files_content("/revistas", "abc", ["a.htm", "b.htm"])
        self.assertIn("not available", content)
        self.assertIn("available body", content)
        self.assertIn("UNAVAILABLE MESSAGE: 1", content)

    def test_migrate_page_content_requires_acron_or_page_name(self):
        with self.assertRaises(IOError):
            migrate_page_content("<p>x</p>", language="pt")

    @patch("webapp.utils.utils.create_image")
    @patch("webapp.utils.utils.create_file")
    def test_migrate_page_create_image_and_file_wrappers(
        self, mocked_create_file, mocked_create_image
    ):
        mocked_create_image.return_value = Mock(get_absolute_url="/media/img.png")
        mocked_create_file.return_value = Mock(get_absolute_url="/media/file.pdf")
        self.assertEqual("/media/img.png", migrate_page_create_image("a", "b.png"))
        self.assertEqual("/media/file.pdf", migrate_page_create_file("a", "b.pdf"))

    @patch("webapp.utils.utils.create_page")
    @patch("webapp.utils.utils.migrate_page_content")
    @patch("webapp.utils.utils.join_html_files_content")
    def test_create_new_journal_page(
        self, mocked_join, mocked_migrate, mocked_create_page
    ):
        mocked_join.return_value = "<p>joined</p>"
        mocked_migrate.return_value = "<p>migrated</p>"
        result = create_new_journal_page("rbep", ["about.htm"], "pt")
        self.assertEqual("<p>migrated</p>", result)
        mocked_create_page.assert_called_once()

    def test_get_resource_url_and_get_resources_url(self):
        match = Mock(language="pt", type="pdf", url="http://example.com/a.pdf")
        mismatch = Mock(language="en", type="pdf", url="http://example.com/b.pdf")
        self.assertEqual("http://example.com/a.pdf", get_resource_url(match, "pdf", "pt"))
        self.assertIsNone(get_resource_url(match, "xml", "pt"))
        self.assertEqual(
            "http://example.com/a.pdf", get_resources_url([mismatch, match], "pdf", "pt")
        )
        self.assertIsNone(get_resources_url([mismatch], "pdf", "pt"))

    def test_utc_to_local(self):
        utc_dt = datetime(2020, 6, 15, 12, 0, 0)
        local_dt = utc_to_local(utc_dt)
        local_tz = pytz.timezone(current_app.config["LOCAL_ZONE"])
        expected = (
            utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
        )
        self.assertEqual(local_tz.normalize(expected), local_dt)

    @patch("webapp.utils.utils.requests.post")
    def test_is_recaptcha_valid(self, mocked_post):
        from webapp.utils.utils import is_recaptcha_valid

        mocked_post.return_value.json.return_value = {"success": True}
        request = Mock()
        request.form = {"g-recaptcha-response": "token"}
        self.assertTrue(is_recaptcha_valid(request))
        mocked_post.assert_called_once()

    def test_asbool_all_branches(self):
        self.assertFalse(asbool(None))
        self.assertTrue(asbool(True))
        self.assertFalse(asbool(False))
        self.assertTrue(asbool("yes"))
        self.assertTrue(asbool("ON"))
        self.assertTrue(asbool("1"))
        self.assertFalse(asbool("no"))
        self.assertFalse(asbool("0"))
        self.assertFalse(asbool("maybe"))

    def test_fix_journal_last_issue_sets_url_segment(self):
        last_issue = test_utils.getLastIssue(
            {"volume": "10", "number": "2", "year": 2020, "suppl_text": "s1"}
        )
        last_issue.url_segment = None
        journal = test_utils.makeOneJournal({"last_issue": last_issue})
        result = fix_journal_last_issue(journal)
        self.assertIsNotNone(result.url_segment)

    def test_fix_journal_last_issue_when_already_set(self):
        last_issue = test_utils.getLastIssue()
        journal = test_utils.makeOneJournal({"last_issue": last_issue})
        original = last_issue.url_segment
        result = fix_journal_last_issue(journal)
        self.assertEqual(original, result.url_segment)

    def test_fix_journal_last_issue_when_no_last_issue(self):
        journal = test_utils.makeOneJournal({"last_issue": None})
        self.assertIsNone(fix_journal_last_issue(journal))

    def test_render_citation(self):
        csl_json = [
            {
                "id": "item1",
                "type": "article-journal",
                "title": "Sample Article",
                "author": [{"family": "Silva", "given": "João"}],
                "issued": {"date-parts": [[2020, 1]]},
            }
        ]
        citations = render_citation(csl_json, style="apa")
        self.assertEqual(1, len(citations))
        self.assertIn("Sample Article", citations[0])

    def test_get_fetch_data_timeout_explicit(self):
        self.assertEqual(42, _get_fetch_data_timeout(42))

    def test_get_fetch_data_timeout_from_app_config(self):
        original = current_app.config.get("FETCH_DATA_TIMEOUT")
        current_app.config["FETCH_DATA_TIMEOUT"] = 25
        try:
            self.assertEqual(25, _get_fetch_data_timeout())
        finally:
            current_app.config["FETCH_DATA_TIMEOUT"] = original

    @patch.dict(os.environ, {"OPAC_FETCH_DATA_TIMEOUT": "7"})
    def test_get_fetch_data_timeout_from_env_without_app_context(self):
        with current_app.app_context():
            pass
        with patch("webapp.utils.utils.has_app_context", return_value=False):
            self.assertEqual(7, _get_fetch_data_timeout())

    @patch("webapp.utils.utils.requests.get")
    def test_fetch_data_connection_error(self, mocked_get):
        mocked_get.side_effect = requests.exceptions.ConnectionError("down")
        with self.assertRaises(RetryableError):
            fetch_data("http://example.com")

    @patch("webapp.utils.utils.requests.get")
    def test_fetch_data_timeout_error(self, mocked_get):
        mocked_get.side_effect = requests.exceptions.Timeout("slow")
        with self.assertRaises(RetryableError):
            fetch_data("http://example.com")

    @patch("webapp.utils.utils.requests.get")
    def test_fetch_data_invalid_schema(self, mocked_get):
        mocked_get.side_effect = requests.exceptions.InvalidSchema("bad")
        with self.assertRaises(NonRetryableError):
            fetch_data("bad://example.com")

    @patch("webapp.utils.utils.requests.get")
    def test_fetch_data_http_404(self, mocked_get):
        response = Mock()
        response.status_code = 404
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
        mocked_get.return_value = response
        with self.assertRaises(NonRetryableError):
            fetch_data("http://example.com/missing")

    @patch("webapp.utils.utils.requests.get")
    def test_fetch_data_http_500(self, mocked_get):
        response = Mock()
        response.status_code = 500
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
        mocked_get.return_value = response
        with self.assertRaises(RetryableError):
            fetch_data("http://example.com/error")

    @patch("webapp.utils.utils.requests.get")
    def test_fetch_data_http_unexpected_status_re_raises(self, mocked_get):
        response = Mock()
        response.status_code = 999
        http_error = requests.HTTPError(response=response)
        response.raise_for_status.side_effect = http_error
        mocked_get.return_value = response
        with self.assertRaises(requests.HTTPError):
            fetch_data("http://example.com/weird")

    @patch("webapp.utils.utils.requests.get")
    def test_fetch_data_json_response(self, mocked_get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ok": True}
        mocked_get.return_value = response
        self.assertEqual({"ok": True}, fetch_data("http://example.com", json=True))

    def test_replace_link(self):
        from bs4 import BeautifulSoup

        html = '<section><a href="http://example.com/page#anchor">link</a></section>'
        section = BeautifulSoup(html, "html.parser").find("section")
        result = replace_link(section)
        self.assertEqual("#anchor", result.find("a")["href"])

    def test_normalize_lang_portuguese(self):
        self.assertEqual("pt-br", normalize_lang_portuguese("pt_BR"))
        self.assertEqual("en", normalize_lang_portuguese("en"))

    def test_extract_section(self):
        html = '<html><section class="journalContent"><p>content</p></section></html>'
        result = extract_section(html, "journalContent")
        self.assertIn("journalContent", result)

    @patch("webapp.utils.utils.replace_link", return_value=None)
    def test_extract_section_returns_none_when_section_missing(self, mocked_replace):
        self.assertIsNone(extract_section("<html></html>", "missing"))
        mocked_replace.assert_called_once()

    @patch("webapp.utils.utils.fetch_data")
    def test_fetch_and_extract_section(self, mocked_fetch):
        html = b'<html><section class="journalContent"><p>core</p></section></html>'
        mocked_fetch.return_value = html
        result = fetch_and_extract_section("scl", "rbep", "pt_BR")
        self.assertIn("core", result)
        mocked_fetch.assert_called_once_with(
            url="http://core.scielo.org/pt-br/journal/scl/rbep/"
        )

    @patch("webapp.utils.utils.Image")
    def test_generate_thumbnail_key_error_returns_none(self, mocked_image_module):
        from webapp.utils.utils import generate_thumbnail

        image_root = tempfile.mkdtemp()
        original_image_root = current_app.config["IMAGE_ROOT"]
        current_app.config["IMAGE_ROOT"] = image_root
        mocked_image_module.open.side_effect = KeyError("bad key")
        try:
            self.assertIsNone(generate_thumbnail("/tmp/fake.png"))
        finally:
            current_app.config["IMAGE_ROOT"] = original_image_root

    @patch("webapp.utils.utils.Image", None)
    def test_generate_thumbnail_when_image_is_none(self):
        from webapp.utils.utils import generate_thumbnail

        self.assertIsNone(generate_thumbnail("/tmp/fake.png"))

    @patch("webapp.create_app")
    @patch("webapp.utils.utils.send_email")
    @patch("webapp.utils.utils.AuditLogEntry")
    def test_send_audit_log_daily_report_disabled(
        self, mocked_audit, mocked_send_email, mocked_create_app
    ):
        mocked_create_app.return_value = current_app._get_current_object()
        original = current_app.config["AUDIT_LOG_NOTIFICATION_ENABLED"]
        current_app.config["AUDIT_LOG_NOTIFICATION_ENABLED"] = False
        try:
            send_audit_log_daily_report()
            mocked_send_email.assert_not_called()
        finally:
            current_app.config["AUDIT_LOG_NOTIFICATION_ENABLED"] = original

    @patch("webapp.create_app")
    @patch("webapp.utils.utils.send_email")
    @patch("webapp.utils.utils.AuditLogEntry")
    def test_send_audit_log_daily_report_no_records(
        self, mocked_audit, mocked_send_email, mocked_create_app
    ):
        mocked_create_app.return_value = current_app._get_current_object()
        queryset = Mock()
        queryset.count.return_value = 0
        mocked_audit.objects.filter.return_value.order_by.return_value = queryset
        original = current_app.config["AUDIT_LOG_NOTIFICATION_ENABLED"]
        current_app.config["AUDIT_LOG_NOTIFICATION_ENABLED"] = True
        try:
            send_audit_log_daily_report()
            mocked_send_email.assert_not_called()
        finally:
            current_app.config["AUDIT_LOG_NOTIFICATION_ENABLED"] = original

    @patch("webapp.create_app")
    @patch("webapp.utils.utils.send_email", return_value=(True, ""))
    @patch("webapp.utils.utils.AuditLogEntry")
    def test_send_audit_log_daily_report_with_records(
        self, mocked_audit, mocked_send_email, mocked_create_app
    ):
        mocked_create_app.return_value = current_app._get_current_object()
        record = Mock()
        record._id = "abc123"
        record.created_at = datetime.now(timezone.utc)
        queryset = Mock()
        queryset.count.return_value = 1
        queryset.__iter__ = Mock(return_value=iter([record]))
        mocked_audit.objects.filter.return_value.order_by.return_value = queryset

        create_user("confirmed@example.com", "secret", True)
        original_enabled = current_app.config["AUDIT_LOG_NOTIFICATION_ENABLED"]
        original_recipients = current_app.config["AUDIT_LOG_NOTIFICATION_RECIPIENTS"]
        current_app.config["AUDIT_LOG_NOTIFICATION_ENABLED"] = True
        current_app.config["AUDIT_LOG_NOTIFICATION_RECIPIENTS"] = [
            "audit@example.com",
            "invalid-email",
        ]
        try:
            send_audit_log_daily_report()
            mocked_send_email.assert_called_once()
            email_kwargs = mocked_send_email.call_args[1]
            self.assertIn("confirmed@example.com", email_kwargs["recipient"])
            self.assertIn("audit@example.com", email_kwargs["recipient"])
        finally:
            current_app.config["AUDIT_LOG_NOTIFICATION_ENABLED"] = original_enabled
            current_app.config["AUDIT_LOG_NOTIFICATION_RECIPIENTS"] = original_recipients

    @patch("webapp.create_app")
    @patch("webapp.utils.utils.send_email")
    @patch("webapp.utils.utils.AuditLogEntry")
    def test_send_audit_log_daily_report_no_valid_conf_recipients(
        self, mocked_audit, mocked_send_email, mocked_create_app
    ):
        mocked_create_app.return_value = current_app._get_current_object()
        record = Mock()
        record._id = "abc123"
        record.created_at = datetime.now(timezone.utc)
        queryset = Mock()
        queryset.count.return_value = 1
        queryset.__iter__ = Mock(return_value=iter([record]))
        mocked_audit.objects.filter.return_value.order_by.return_value = queryset

        original_enabled = current_app.config["AUDIT_LOG_NOTIFICATION_ENABLED"]
        original_recipients = current_app.config["AUDIT_LOG_NOTIFICATION_RECIPIENTS"]
        current_app.config["AUDIT_LOG_NOTIFICATION_ENABLED"] = True
        current_app.config["AUDIT_LOG_NOTIFICATION_RECIPIENTS"] = ["not-an-email"]
        try:
            send_audit_log_daily_report()
            mocked_send_email.assert_called_once()
        finally:
            current_app.config["AUDIT_LOG_NOTIFICATION_ENABLED"] = original_enabled
            current_app.config["AUDIT_LOG_NOTIFICATION_RECIPIENTS"] = original_recipients


class UtilsPILImportCoverageTestCase(BaseTestCase):
    def test_pil_import_error_sets_image_to_none(self):
        saved_modules = sys.modules.copy()
        saved_utils = sys.modules.get("webapp.utils.utils")
        try:
            sys.modules["PIL"] = None
            sys.modules["PIL.Image"] = None
            if "webapp.utils.utils" in sys.modules:
                del sys.modules["webapp.utils.utils"]
            utils_module = importlib.import_module("webapp.utils.utils")
            self.assertIsNone(utils_module.Image)
        finally:
            sys.modules.clear()
            sys.modules.update(saved_modules)
            if saved_utils is not None:
                sys.modules["webapp.utils.utils"] = saved_utils
