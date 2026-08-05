# coding: utf-8
"""Tests for CKEditor 5 integration on admin Pages create/edit."""

import os

from flask import current_app, url_for
from opac_schema.v1.models import Pages
from tests.test_admin_views_coverage import AdminViewsCoverageMixin
from tests.utils import makeOnePage
from webapp.admin.custom_widget import CKEditorField
from wtforms import Form

from .base import BaseTestCase

CKEDITOR5_STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "webapp",
    "static",
    "js",
    "ckeditor5",
)

RICH_HTML = (
    '<p style="text-align:justify;">Justificado com '
    '<span style="color:#c00;">cor</span> e '
    '<a href="https://www.scielo.br">link</a>.</p>'
    "<ul><li>item um</li><li>item dois</li></ul>"
    "<table><tbody><tr><td>celula</td></tr></tbody></table>"
)


class PagesCKEditor5Tests(AdminViewsCoverageMixin, BaseTestCase):
    def test_ckeditor5_static_assets_exist(self):
        expected = [
            "ckeditor5.umd.js",
            "ckeditor5.css",
            "opac-pages-editor.js",
            os.path.join("translations", "pt-br.umd.js"),
            os.path.join("translations", "es.umd.js"),
        ]
        for relative in expected:
            path = os.path.join(CKEDITOR5_STATIC_DIR, relative)
            self.assertTrue(os.path.isfile(path), "missing asset: %s" % path)

        editor_js = open(
            os.path.join(CKEDITOR5_STATIC_DIR, "opac-pages-editor.js"), encoding="utf-8"
        ).read()
        self.assertIn('licenseKey: "GPL"', editor_js)
        self.assertIn("htmlSupport", editor_js)
        self.assertIn("ClassicEditor.create", editor_js)
        self.assertIn("OPAC_CKEDITOR_LANG", editor_js)
        for feature in (
            "Fullscreen",
            "HtmlEmbed",
            "MediaEmbed",
            "CodeBlock",
            "TodoList",
            "SpecialCharacters",
            "Emoji",
            "FindAndReplace",
            "WordCount",
            "menuBar",
        ):
            self.assertIn(feature, editor_js)

    def test_ckeditor_field_renders_textarea_with_ckeditor_class(self):
        class DummyForm(Form):
            content = CKEditorField()

        form = DummyForm(data={"content": "<p>hello</p>"})
        html = str(form.content())
        self.assertIn('id="content"', html)
        self.assertIn('name="content"', html)
        self.assertIn("ckeditor", html)
        self.assertIn("&lt;p&gt;hello&lt;/p&gt;", html)

    def test_pages_create_form_loads_ckeditor5_assets(self):
        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    with client.session_transaction() as sess:
                        sess["lang"] = "pt_BR"
                    response = client.get("/admin/pages/new/")
                    self.assertStatus(response, 200)
                    self.assertTemplateUsed("admin/pages/add.html")
                    body = response.get_data(as_text=True)
                    self.assertIn("/static/js/ckeditor5/ckeditor5.css", body)
                    self.assertIn("/static/js/ckeditor5/ckeditor5.umd.js", body)
                    self.assertIn(
                        "/static/js/ckeditor5/translations/pt-br.umd.js", body
                    )
                    self.assertIn('window.OPAC_CKEDITOR_LANG = "pt-br"', body)
                    self.assertIn("/static/js/ckeditor5/opac-pages-editor.js", body)
                    self.assertIn('id="content"', body)
                    self.assertNotIn("/static/js/ckeditor/ckeditor.js", body)

    def test_pages_form_uses_admin_session_language_for_ckeditor(self):
        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)

                    with client.session_transaction() as sess:
                        sess["lang"] = "es"
                    es_body = client.get("/admin/pages/new/").get_data(as_text=True)
                    self.assertIn(
                        "/static/js/ckeditor5/translations/es.umd.js", es_body
                    )
                    self.assertIn('window.OPAC_CKEDITOR_LANG = "es"', es_body)
                    self.assertNotIn(
                        "/static/js/ckeditor5/translations/pt-br.umd.js", es_body
                    )

                    with client.session_transaction() as sess:
                        sess["lang"] = "en"
                    en_body = client.get("/admin/pages/new/").get_data(as_text=True)
                    self.assertIn('window.OPAC_CKEDITOR_LANG = "en"', en_body)
                    self.assertNotIn(
                        "/static/js/ckeditor5/translations/pt-br.umd.js", en_body
                    )
                    self.assertNotIn(
                        "/static/js/ckeditor5/translations/es.umd.js", en_body
                    )

    def test_pages_edit_form_loads_ckeditor5_assets(self):
        page = makeOnePage({"content": "<p>conteudo inicial</p>"})
        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    with client.session_transaction() as sess:
                        sess["lang"] = "pt_BR"
                    response = client.get("/admin/pages/edit/?id=%s" % page.id)
                    self.assertStatus(response, 200)
                    self.assertTemplateUsed("admin/pages/edit.html")
                    body = response.get_data(as_text=True)
                    self.assertIn("/static/js/ckeditor5/ckeditor5.umd.js", body)
                    self.assertIn("/static/js/ckeditor5/opac-pages-editor.js", body)
                    self.assertIn('window.OPAC_CKEDITOR_LANG = "pt-br"', body)
                    self.assertIn("conteudo inicial", body)
                    self.assertNotIn("/static/js/ckeditor/ckeditor.js", body)

    def test_pages_create_saves_rich_html_content(self):
        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    response = client.post(
                        "/admin/pages/new/",
                        data={
                            "name": "pagina-ck5-create",
                            "slug_name": "pagina-ck5-create",
                            "content": RICH_HTML,
                            "language": "pt_BR",
                            "description": "descricao create",
                            "journal": "",
                        },
                        follow_redirects=True,
                    )
                    self.assertStatus(response, 200)
                    created = Pages.objects(name="pagina-ck5-create").first()
                    self.assertIsNotNone(created)
                    self.assertIn("text-align:justify", created.content)
                    self.assertIn("https://www.scielo.br", created.content)
                    self.assertIn("<table>", created.content)
                    self.assertIn("celula", created.content)

    def test_pages_edit_updates_rich_html_content(self):
        page = makeOnePage(
            {
                "name": "pagina-ck5-edit",
                "slug_name": "pagina-ck5-edit",
                "content": "<p>antes</p>",
                "description": "old",
            }
        )
        with current_app.app_context():
            self._admin_context()
            with current_app.test_request_context():
                with self.client as client:
                    self._login_as_admin(client)
                    response = client.post(
                        "/admin/pages/edit/?id=%s" % page.id,
                        data={
                            "name": page.name,
                            "slug_name": page.slug_name,
                            "content": RICH_HTML,
                            "language": page.language,
                            "description": "descricao edit",
                            "journal": "",
                        },
                        follow_redirects=True,
                    )
                    self.assertStatus(response, 200)
                    self.assertIn("success", response.get_data(as_text=True))

                    updated = Pages.objects.get(_id=page.id)
                    self.assertEqual(updated.description, "descricao edit")
                    self.assertIn("Justificado com", updated.content)
                    self.assertIn('style="color:#c00;"', updated.content)
                    self.assertIn("item dois", updated.content)
                    self.assertNotIn("<p>antes</p>", updated.content)

                    details = client.get(url_for("pages.details_view", id=page.id))
                    self.assertStatus(details, 200)
                    details_body = details.get_data(as_text=True)
                    self.assertIn("https://www.scielo.br", details_body)
                    self.assertIn("celula", details_body)
