# coding: utf-8

from flask import current_app, url_for

from . import utils
from .base import BaseTestCase


class HomeTestCase(BaseTestCase):
    def test_collection_trans_home(self):
        """
        Verificamos se a home esta com as traduções corretas para o nome da
        coleção.
        """

        with current_app.app_context():
            utils.makeOneCollection(
                {
                    "name_pt": "coleção falsa",
                    "name_es": "colección falsa",
                    "name_en": "dummy collection",
                }
            )

            with self.client as c:
                # idioma em 'pt_br'
                response = c.get(
                    url_for("main.set_locale", lang_code="pt_BR"),
                    headers={"Referer": "/"},
                    follow_redirects=True,
                )

                self.assertStatus(response, 200)
                expected_anchor = "coleção falsa"
                self.assertIn(expected_anchor, response.data.decode("utf-8"))

                # idioma em 'en'
                response = c.get(
                    url_for("main.set_locale", lang_code="en"),
                    headers={"Referer": "/"},
                    follow_redirects=True,
                )

                self.assertStatus(response, 200)
                expected_anchor = "dummy collection"
                self.assertIn(expected_anchor, response.data.decode("utf-8"))

                # idioma em 'es'
                response = c.get(
                    url_for("main.set_locale", lang_code="es"),
                    headers={"Referer": "/"},
                    follow_redirects=True,
                )

                self.assertStatus(response, 200)
                expected_anchor = "colección falsa"
                self.assertIn(expected_anchor, response.data.decode("utf-8"))

    def test_home_logo_shown_when_configured(self):
        """
        Verificamos se a home exibe o logo da coleção quando está configurado.
        """

        with current_app.app_context():
            utils.makeOneCollection(
                {
                    "name_pt": "coleção falsa",
                    "home_logo_pt": "http://example.com/logo_pt.png",
                    "home_logo_en": "http://example.com/logo_en.png",
                    "home_logo_es": "http://example.com/logo_es.png",
                }
            )

            with self.client as c:
                # idioma em 'pt_br'
                response = c.get(
                    url_for("main.set_locale", lang_code="pt_BR"),
                    headers={"Referer": "/"},
                    follow_redirects=True,
                )

                self.assertStatus(response, 200)
                self.assertIn(
                    "http://example.com/logo_pt.png",
                    response.data.decode("utf-8"),
                )
                self.assertNotIn(
                    'id="collectionNameHome"', response.data.decode("utf-8")
                )

                # idioma em 'en'
                response = c.get(
                    url_for("main.set_locale", lang_code="en"),
                    headers={"Referer": "/"},
                    follow_redirects=True,
                )

                self.assertStatus(response, 200)
                self.assertIn(
                    "http://example.com/logo_en.png",
                    response.data.decode("utf-8"),
                )

    def test_home_logo_fallback_to_text_when_not_configured(self):
        """
        Verificamos se a home exibe o nome da coleção em texto quando não há logo configurado.
        """

        with current_app.app_context():
            utils.makeOneCollection({"name_pt": "coleção falsa"})

            with self.client as c:
                response = c.get(
                    url_for("main.set_locale", lang_code="pt_BR"),
                    headers={"Referer": "/"},
                    follow_redirects=True,
                )

                self.assertStatus(response, 200)
                self.assertIn(
                    'id="collectionNameHome"', response.data.decode("utf-8")
                )
                self.assertIn("coleção falsa", response.data.decode("utf-8"))

    def test_home_aria_label_uses_collection_name(self):
        """
        Verificamos se o aria-label usa o nome dinâmico da coleção.
        """

        with current_app.app_context():
            utils.makeOneCollection({"name_pt": "coleção falsa"})

            with self.client as c:
                response = c.get(
                    url_for("main.set_locale", lang_code="pt_BR"),
                    headers={"Referer": "/"},
                    follow_redirects=True,
                )

                self.assertStatus(response, 200)
                self.assertIn(
                    'aria-label="Acessar site coleção coleção falsa"',
                    response.data.decode("utf-8"),
                )
