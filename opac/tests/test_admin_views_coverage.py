# coding: utf-8
"""Additional tests to reach full coverage of webapp.admin.views."""

import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from flask import current_app, g, url_for
from flask_login import current_user
from markupsafe import Markup
from mongoengine.errors import NotUniqueError
from opac_schema.v1.models import AuditLogEntry, Collection, News, Pages, PressRelease, Sponsor
from tests.utils import (
    makeOneArticle,
    makeOneCollection,
    makeOneIssue,
    makeOneJournal,
    makeOnePage,
    makeOneSponsor,
)
from webapp import dbsql
from webapp.admin.views import (
    AuditLogEntryAdminView,
    CollectionAdminView,
    FileAdminView,
    ImageAdminView,
    JournalAdminView,
    NewsAdminView,
    PagesAdminView,
    SponsorAdminView,
)
from webapp.models import File, Image, User
from webapp.utils import create_user

from .base import BaseTestCase


ADMIN_USER = {"email": "admin@opac.org", "password": "foobarbaz"}


class AdminViewsCoverageMixin(object):
    def _login_as_admin(self, client):
        create_user(ADMIN_USER["email"], ADMIN_USER["password"], True)
        login_url = url_for("admin.login_view")
        response = client.post(login_url, data=ADMIN_USER, follow_redirects=True)
        self.assertStatus(response, 200)
        self.assertTrue(current_user.is_authenticated)
        return response

    def _admin_context(self):
        collection = makeOneCollection()
        g.collection = collection
        return collection


class AdminIndexCoverageTests(AdminViewsCoverageMixin, BaseTestCase):
    def test_login_unconfirmed_user_shows_unconfirm_template(self):
        credentials = {"email": "unconfirmed@example.com", "password": "secret123"}
        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    create_user(credentials["email"], credentials["password"], False)
                    response = client.post(
                        url_for("admin.login_view"),
                        data=credentials,
                        follow_redirects=True,
                    )
                    self.assertStatus(response, 200)
                    self.assertTemplateUsed("admin/auth/unconfirm_email.html")

    def test_reset_password_email_send_failure_shows_error_flash(self):
        credentials = {"email": "reset-fail@example.com", "password": "secret123"}
        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    create_user(credentials["email"], credentials["password"], True)
                    user = User.query.filter_by(email=credentials["email"]).one()
                    with patch.object(
                        user,
                        "send_reset_password_email",
                        return_value=(False, "smtp down"),
                    ):
                        with patch(
                            "webapp.admin.views.controllers.get_user_by_email",
                            return_value=user,
                        ):
                            response = client.post(
                                url_for("admin.reset"),
                                data={"email": credentials["email"]},
                                follow_redirects=True,
                            )
                    self.assertStatus(response, 200)
                    self.assertIn("smtp down", response.data.decode("utf-8"))


class UserAdminCoverageTests(AdminViewsCoverageMixin, BaseTestCase):
    def test_after_model_change_email_send_success_flash(self):
        new_user = {"email": "new-user@example.com"}
        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    with patch(
                        "webapp.models.User.send_confirmation_email",
                        return_value=(True, ""),
                    ):
                        response = client.post(
                            "/admin/user/new/",
                            data={"email": new_user["email"]},
                            follow_redirects=True,
                        )
                    self.assertStatus(response, 200)
                    self.assertIn(
                        "Enviamos o email de confirmação para: %s" % new_user["email"],
                        response.data.decode("utf-8"),
                    )

    def test_after_model_change_email_send_failure_flash(self):
        new_user = {"email": "fail-user@example.com"}
        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    with patch(
                        "webapp.models.User.send_confirmation_email",
                        return_value=(False, "mail error"),
                    ):
                        response = client.post(
                            "/admin/user/new/",
                            data={"email": new_user["email"]},
                            follow_redirects=True,
                        )
                    self.assertStatus(response, 200)
                    self.assertIn("mail error", response.data.decode("utf-8"))

    def test_after_model_change_email_send_raises_socket_error(self):
        new_user = {"email": "socket-user@example.com"}

        class SendErr(ValueError):
            message = "connection refused"

        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    with patch(
                        "webapp.models.User.send_confirmation_email",
                        side_effect=SendErr(),
                    ):
                        response = client.post(
                            "/admin/user/new/",
                            data={"email": new_user["email"]},
                            follow_redirects=True,
                        )
                    self.assertStatus(response, 200)
                    self.assertIn(
                        "connection refused", response.data.decode("utf-8")
                    )

    def test_action_send_confirm_email_partial_failure(self):
        target = {"email": "partial@example.com", "password": "123"}
        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    create_user(target["email"], target["password"], False)
                    user = User.query.filter_by(email=target["email"]).one()

                    def fake_send():
                        return (False, "cannot send")

                    with patch.object(user, "send_confirmation_email", fake_send):
                        with patch(
                            "webapp.admin.views.models.User.query"
                        ) as mock_query:
                            mock_query.filter.return_value.all.return_value = [user]
                            response = client.post(
                                "/admin/user/action/",
                                data={
                                    "action": "confirm_email",
                                    "rowid": user.id,
                                    "url": "/admin/user/",
                                },
                                follow_redirects=True,
                            )
                    self.assertStatus(response, 200)
                    self.assertIn(
                        "Ocorreu um erro no envio do email de confirmação",
                        response.data.decode("utf-8"),
                    )

    def test_action_send_confirm_email_exception(self):
        target = {"email": "exception@example.com", "password": "123"}
        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    create_user(target["email"], target["password"], False)
                    user = User.query.filter_by(email=target["email"]).one()
                    with patch.object(
                        User,
                        "send_confirmation_email",
                        side_effect=RuntimeError("db broken"),
                    ):
                        response = client.post(
                            "/admin/user/action/",
                            data={
                                "action": "confirm_email",
                                "rowid": user.id,
                                "url": "/admin/user/",
                            },
                            follow_redirects=True,
                        )
                    self.assertStatus(response, 200)
                    self.assertIn("db broken", response.data.decode("utf-8"))


class AssetsAdminCoverageTests(AdminViewsCoverageMixin, BaseTestCase):
    def _create_file(self, **kwargs):
        record = File(
            name=kwargs.get("name", "sample-file"),
            path=kwargs.get("path", "files/sample.pdf"),
            language=kwargs.get("language", "pt"),
        )
        dbsql.session.add(record)
        dbsql.session.commit()
        return record

    def _create_image(self, **kwargs):
        record = Image(
            name=kwargs.get("name", "sample-image"),
            path=kwargs.get("path", "images/sample.png"),
            language=kwargs.get("language", "pt"),
        )
        dbsql.session.add(record)
        dbsql.session.commit()
        return record

    def test_file_admin_formatters_and_search_placeholder(self):
        with current_app.app_context():
            record = self._create_file()
            view = FileAdminView(File, dbsql)
            path_html = view._path_formatter(None, record, "path")
            self.assertIn("Open", str(path_html))
            self.assertIn(record.get_absolute_url, str(path_html))
            self.assertEqual(view.search_placeholder(), "Nome")

            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    response = client.get(url_for("file.index_view"))
                    self.assertStatus(response, 200)

    def test_image_admin_formatters_and_search_placeholder(self):
        with current_app.app_context():
            record = self._create_image()
            view = ImageAdminView(Image, dbsql)
            path_html = view._path_formatter(None, record, "path")
            self.assertIn("Open", str(path_html))

            empty_preview = view._preview_formatter(
                None, Image(name="x", path=""), "preview"
            )
            self.assertEqual(empty_preview, "")

            preview_html = view._preview_formatter(None, record, "preview")
            self.assertIn("<img", str(preview_html))
            self.assertEqual(view.search_placeholder(), "Nome")

            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    response = client.get(url_for("image.index_view"))
                    self.assertStatus(response, 200)


class NewsAdminCoverageTests(BaseTestCase):
    def _make_news(self, **kwargs):
        news_id = kwargs.pop("_id", str(uuid4().hex))
        news = News(
            _id=news_id,
            title=kwargs.get("title", "SciELO News"),
            description=kwargs.get("description", "Description"),
            url=kwargs.get("url", "http://example.com/news"),
            language=kwargs.get("language", "pt"),
            is_public=kwargs.get("is_public", True),
            publication_date=kwargs.get(
                "publication_date", datetime.datetime(2024, 1, 15, 12, 0, 0)
            ),
            image_url=kwargs.get("image_url", ""),
        )
        news.save()
        return news

    def test_news_admin_formatters(self):
        news = self._make_news(image_url="http://example.com/img.png")
        view = NewsAdminView(News)

        url_html = view._url_formatter(None, news, "url")
        self.assertIn("Open", str(url_html))

        news_without_image = News(
            _id=str(uuid4().hex),
            title="No image",
            description="Description",
            url="http://example.com/news",
            language="pt",
            is_public=True,
            publication_date=datetime.datetime(2024, 1, 15, 12, 0, 0),
        )
        self.assertEqual(
            view._preview_formatter(None, news_without_image, "image_url"), ""
        )
        preview_html = view._preview_formatter(None, news, "image_url")
        self.assertIn("<img", str(preview_html))

        date_value = view._preview_date_format(None, news, "publication_date")
        self.assertIsNotNone(date_value)


class OpacBaseAdminSearchTests(BaseTestCase):
    def test_opac_base_admin_search_multiple_fields(self):
        makeOneJournal({"title": "Alpha Journal", "acronym": "alph"})
        makeOneJournal({"title": "Beta Journal", "acronym": "beta"})

        from opac_schema.v1.models import Journal

        view = JournalAdminView(Journal)
        view._search_fields = [
            Journal._fields["title"],
            Journal._fields["acronym"],
        ]
        results = list(view._search(Journal.objects, "Alpha"))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Alpha Journal")


class SponsorCollectionCoverageTests(AdminViewsCoverageMixin, BaseTestCase):
    def test_sponsor_create_sets_id_on_model_change(self):
        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    response = client.post(
                        "/admin/sponsor/new/",
                        data={
                            "order": "99",
                            "name": "New Sponsor %s" % uuid4().hex[:8],
                            "url": "http://example.com",
                            "logo_url": "http://example.com/logo.png",
                        },
                        follow_redirects=True,
                    )
                    self.assertStatus(response, 200)
                    self.assertTemplateUsed("admin/model/list.html")

    def test_sponsor_handle_view_exception_not_unique(self):
        from webapp.admin.views import SponsorAdminView
        from opac_schema.v1.models import Sponsor

        view = SponsorAdminView(Sponsor)
        handled = view.handle_view_exception(NotUniqueError("duplicate"))
        self.assertTrue(handled)

        not_handled = view.handle_view_exception(ValueError("other"))
        self.assertFalse(not_handled)

    def test_collection_create_sets_id_on_model_change(self):
        view = CollectionAdminView(Collection)
        model = Collection(acronym="newcol", name="New Collection")
        view.on_model_change(MagicMock(), model, True)
        self.assertTrue(model._id)


class ArticleFullTextCoverageTests(AdminViewsCoverageMixin, BaseTestCase):
    def test_set_full_text_unavailable_success_and_failure(self):
        article = makeOneArticle({"display_full_text": True})

        with current_app.app_context():
            article_index_url = url_for("article.index_view")
            action_url = "%saction/" % article_index_url
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    response = client.post(
                        action_url,
                        data={
                            "url": article_index_url,
                            "action": "set_full_text_unavailable",
                            "rowid": article.id,
                        },
                        follow_redirects=True,
                    )
                    self.assertIn(
                        "Texto completo foi indisponibilizado",
                        response.data.decode("utf-8"),
                    )

                    with patch(
                        "webapp.admin.views.controllers.set_article_display_full_text_bulk",
                        side_effect=RuntimeError("boom"),
                    ):
                        response = client.post(
                            action_url,
                            data={
                                "url": article_index_url,
                                "action": "set_full_text_unavailable",
                                "rowid": article.id,
                            },
                            follow_redirects=True,
                        )
                    self.assertIn("boom", response.data.decode("utf-8"))

    def test_set_full_text_available_success_and_failure(self):
        article = makeOneArticle({"display_full_text": False})

        with current_app.app_context():
            article_index_url = url_for("article.index_view")
            action_url = "%saction/" % article_index_url
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    response = client.post(
                        action_url,
                        data={
                            "url": article_index_url,
                            "action": "set_full_text_available",
                            "rowid": article.id,
                        },
                        follow_redirects=True,
                    )
                    self.assertIn(
                        "Texto completo foi disponibilizado",
                        response.data.decode("utf-8"),
                    )

                    with patch(
                        "webapp.admin.views.controllers.set_article_display_full_text_bulk",
                        side_effect=RuntimeError("kaboom"),
                    ):
                        response = client.post(
                            action_url,
                            data={
                                "url": article_index_url,
                                "action": "set_full_text_available",
                                "rowid": article.id,
                            },
                            follow_redirects=True,
                        )
                    self.assertIn("kaboom", response.data.decode("utf-8"))


class PagesAdminCoverageTests(AdminViewsCoverageMixin, BaseTestCase):
    def test_save_ajax_view_success_and_failure(self):
        page = makeOnePage()
        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    ok = client.post(
                        "/admin/pages/ajx/?id=%s" % page.id,
                        data={
                            "name": page.name,
                            "content": page.content,
                            "language": page.language,
                            "description": page.description,
                        },
                    )
                    self.assertStatus(ok, 200)
                    self.assertEqual(ok.json["saved"], True)

                    bad = client.post(
                        "/admin/pages/ajx/?id=%s" % page.id,
                        data={},
                    )
                    self.assertStatus(bad, 200)
                    self.assertEqual(bad.json["saved"], False)

    def test_preview_view_with_and_without_latest_issue(self):
        from tests.utils import getLastIssue

        journal = makeOneJournal(
            {
                "acronym": "prevj",
                "last_issue": getLastIssue(
                    {"volume": "9", "number": "2", "year": 2024, "suppl_text": ""}
                ),
            }
        )
        makeOneIssue({"journal": journal, "is_public": True})
        page = makeOnePage(
            {
                "journal": journal.acronym,
                "language": "pt_BR",
                "content": "<p>About content</p>",
            }
        )
        journal_no_issue = makeOneJournal({"acronym": "noiss"})
        page_no_issue = makeOnePage(
            {"journal": journal_no_issue.acronym, "language": "en_US"}
        )
        page_no_issue.updated_at = None

        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    with patch(
                        "webapp.admin.views.render_template",
                        return_value="preview-html",
                    ) as mock_render:
                        response = client.get(
                            "/admin/pages/preview/",
                            query_string={"id": page.id},
                        )
                        self.assertStatus(response, 200)
                        self.assertEqual(response.get_data(as_text=True), "preview-html")
                        self.assertEqual(
                            mock_render.call_args[0][0], "journal/about.html"
                        )
                        self.assertIn(
                            "About content", mock_render.call_args[1]["content"]
                        )
                        self.assertIsNotNone(
                            mock_render.call_args[1]["latest_issue_legend"]
                        )

                        response = client.get(
                            "/admin/pages/preview/",
                            query_string={"id": page_no_issue.id},
                        )
                        self.assertStatus(response, 200)
                        self.assertIsNone(
                            mock_render.call_args[1]["latest_issue_legend"]
                        )

    def test_preview_skips_page_updated_at_when_missing(self):
        journal = makeOneJournal({"acronym": "noupdt"})
        page = makeOnePage({"journal": journal.acronym, "language": "pt_BR"})
        page.updated_at = None

        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    with patch(
                        "webapp.admin.views.controllers.get_page_by_id",
                        return_value=page,
                    ):
                        with patch(
                            "webapp.admin.views.render_template",
                            return_value="preview-html",
                        ) as mock_render:
                            response = client.get(
                                "/admin/pages/preview/",
                                query_string={"id": page.id},
                            )
                            self.assertStatus(response, 200)
                            self.assertNotIn(
                                "page_updated_at", mock_render.call_args[1]
                            )

    def test_pages_formatters_and_model_hooks(self):
        view = PagesAdminView(Pages)
        page = makeOnePage({"content": "<strong>HTML</strong>"})
        self.assertIn("HTML", str(view._content_formatter(None, page, "content")))

        dated_page = makeOnePage()
        self.assertIn(
            "-",
            view._created_at_formatter(None, dated_page, "created_at"),
        )
        self.assertIn(
            "-",
            view._updated_at_formatter(None, dated_page, "updated_at"),
        )

        empty_dates = Pages(
            _id=str(uuid4().hex),
            name="nodates",
            slug_name="nodates",
            content="x",
            language="pt_BR",
        )
        self.assertEqual(view._created_at_formatter(None, empty_dates, "created_at"), "")
        self.assertEqual(view._updated_at_formatter(None, empty_dates, "updated_at"), "")

        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    create_response = client.post(
                        "/admin/pages/new/",
                        data={
                            "name": "created-page",
                            "slug_name": "created-page",
                            "content": "<p>new</p>",
                            "language": "pt_BR",
                            "description": "desc",
                            "journal": "",
                        },
                        follow_redirects=True,
                    )
                    self.assertStatus(create_response, 200)
                    created = Pages.objects(name="created-page").first()
                    self.assertIsNotNone(created)

                    create_form = MagicMock()
                    create_form._fields = {
                        "name": MagicMock(data="brand-new-page"),
                        "language": MagicMock(data="pt_BR"),
                        "content": MagicMock(data="<p>brand new</p>"),
                        "journal": MagicMock(data=""),
                        "description": MagicMock(data="desc"),
                    }
                    new_page = Pages(
                        _id=str(uuid4().hex),
                        name="brand-new-page",
                        slug_name="brand-new-page",
                        content="<p>brand new</p>",
                        language="pt_BR",
                        description="desc",
                    )
                    view.on_model_change(create_form, new_page, True)

                    form = MagicMock()
                    form._fields = {
                        "name": MagicMock(data=created.name),
                        "language": MagicMock(data=created.language),
                        "content": MagicMock(data="<p>updated</p>"),
                        "journal": MagicMock(data=created.journal),
                        "description": MagicMock(data="updated desc"),
                    }
                    view.on_model_change(form, created, False)
                    view.on_model_delete(created)

                    self.assertTrue(
                        AuditLogEntry.objects(
                            object_pk=created._id, action="UPD"
                        ).count()
                        >= 1
                    )
                    self.assertTrue(
                        AuditLogEntry.objects(
                            object_pk=created._id, action="DEL"
                        ).count()
                        >= 1
                    )


class PressReleaseAdminCoverageTests(AdminViewsCoverageMixin, BaseTestCase):
    def _make_press_release(self):
        journal = makeOneJournal()
        issue = makeOneIssue({"journal": journal})
        article = makeOneArticle({"journal": journal, "issue": issue})
        pr = PressRelease(
            _id=str(uuid4().hex),
            title="Press title",
            language="pt",
            content="<p>PR content</p>",
            journal=journal.id,
            issue=issue.id,
            article=article.id,
            doi="10.0000/example",
            url="http://example.com/pr",
            publication_date=datetime.datetime(2024, 2, 1),
        )
        pr.save()
        return pr

    def test_press_release_list_and_details(self):
        pr = self._make_press_release()
        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    list_response = client.get(url_for("pressrelease.index_view"))
                    self.assertStatus(list_response, 200)
                    self.assertIn(pr.title, list_response.data.decode("utf-8"))

                    detail_response = client.get(
                        url_for("pressrelease.details_view", id=pr.id)
                    )
                    self.assertStatus(detail_response, 200)
                    self.assertTemplateUsed("admin/model/details.html")


class AuditLogEntryAdminCoverageTests(BaseTestCase):
    def test_audit_log_entry_formatters(self):
        view = AuditLogEntryAdminView(AuditLogEntry)

        no_date = AuditLogEntry(
            _id=str(uuid4().hex),
            action="ADD",
            object_class_name="Page",
            object_pk="page-id",
        )
        self.assertEqual(view._created_at_formatter(None, no_date, "created_at"), "")

        with_date = AuditLogEntry(
            _id=str(uuid4().hex),
            action="UPD",
            created_at=datetime.datetime(2024, 3, 4, 10, 30, 0),
            object_class_name="Page",
            object_pk="page-id",
        )
        self.assertIn("2024-03-04", view._created_at_formatter(None, with_date, "created_at"))

        for action in ("ADD", "UPD", "DEL"):
            entry = AuditLogEntry(
                _id=str(uuid4().hex),
                action=action,
                object_class_name="Page",
                object_pk="pk-%s" % action,
            )
            html = view._action_formatter(None, entry, "action")
            self.assertIsInstance(html, Markup)

        no_action = AuditLogEntry(
            _id=str(uuid4().hex),
            object_class_name="Page",
            object_pk="pk-none",
        )
        self.assertEqual(view._action_formatter(None, no_action, "action"), "?")

        with current_app.app_context():
            page_link = view._object_pk_formatter(
                None,
                AuditLogEntry(
                    _id=str(uuid4().hex),
                    object_class_name="Page",
                    object_pk="linked-page",
                ),
                "object_pk",
            )
            self.assertIn("linked-page", str(page_link))

            plain_pk = view._object_pk_formatter(
                None,
                AuditLogEntry(
                    _id=str(uuid4().hex),
                    object_class_name="Journal",
                    object_pk="journal-id",
                ),
                "object_pk",
            )
            self.assertEqual(plain_pk, "journal-id")

            fields_html = view._fields_data_formatter(
                None,
                AuditLogEntry(
                    _id=str(uuid4().hex),
                    fields_data={
                        "name": {"old_value": "a", "new_value": "b"},
                    },
                ),
                "fields_data",
            )
            self.assertIsInstance(fields_html, Markup)

            empty_fields = view._fields_data_formatter(
                None,
                AuditLogEntry(_id=str(uuid4().hex)),
                "fields_data",
            )
            self.assertEqual(empty_fields, "")


class AdminIndexCountsExtendedTests(AdminViewsCoverageMixin, BaseTestCase):
    def test_admin_index_includes_news_sponsor_pressrelease_counts(self):
        News(
            _id=str(uuid4().hex),
            title="n",
            description="d",
            url="http://example.com",
            language="pt",
            is_public=True,
            publication_date=datetime.datetime.now(),
        ).save()
        makeOneSponsor()
        PressRelease(
            _id=str(uuid4().hex),
            title="pr",
            language="pt",
            content="c",
            url="http://example.com/pr",
            publication_date=datetime.datetime.now(),
        ).save()

        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    response = client.get(url_for("admin.index"))
                    counts = self.get_context_variable("counts")
                    self.assertGreaterEqual(counts["news_total_count"], 1)
                    self.assertGreaterEqual(counts["sponsors_total_count"], 1)
                    self.assertGreaterEqual(counts["pressrelease_total_count"], 1)


class AdminViewsRemainingBranchTests(AdminViewsCoverageMixin, BaseTestCase):
    def test_assets_search_placeholder_without_searchable_columns(self):
        file_view = FileAdminView(File, dbsql)
        file_view.column_searchable_list = []
        self.assertIsNone(file_view.search_placeholder())

        image_view = ImageAdminView(Image, dbsql)
        image_view.column_searchable_list = []
        self.assertIsNone(image_view.search_placeholder())

    def test_sponsor_and_collection_on_model_change_update_paths(self):
        sponsor_view = SponsorAdminView(Sponsor)
        sponsor = makeOneSponsor()
        sponsor_view.on_model_change(MagicMock(), sponsor, False)

        collection_view = CollectionAdminView(Collection)
        collection = makeOneCollection()
        collection_view.on_model_change(MagicMock(), collection, False)

    def test_user_after_model_change_on_update_does_not_send_email(self):
        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    create_user("editable@example.com", "secret", True)
                    user = User.query.filter_by(email="editable@example.com").one()
                    with patch(
                        "webapp.models.User.send_confirmation_email"
                    ) as mock_send:
                        response = client.post(
                            "/admin/user/edit/?id=%s" % user.id,
                            data={"email": "editable@example.com"},
                            follow_redirects=True,
                        )
                        self.assertStatus(response, 200)
                        mock_send.assert_not_called()

    def test_pages_hooks_without_authenticated_user(self):
        view = PagesAdminView(Pages)
        page = makeOnePage()
        form = MagicMock()
        form._fields = {
            "name": MagicMock(data=page.name),
            "language": MagicMock(data=page.language),
            "content": MagicMock(data=page.content),
            "journal": MagicMock(data=page.journal),
            "description": MagicMock(data=page.description),
        }

        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                anonymous = MagicMock()
                anonymous.is_authenticated = False
                with patch("webapp.admin.views.login.current_user", anonymous):
                    view.on_model_change(form, page, False)
                    view.on_model_delete(page)

                    audit_entries = AuditLogEntry.objects(object_pk=page._id)
                    for entry in audit_entries:
                        self.assertIsNone(entry.user)
