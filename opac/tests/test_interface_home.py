# coding: utf-8

from datetime import datetime
from uuid import uuid4

from flask import current_app, url_for
from opac_schema.v1.models import News

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
                self.assertIn('id="collectionNameHome"', response.data.decode("utf-8"))
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
                    'aria-label="Acessar site da coleção coleção falsa"',
                    response.data.decode("utf-8"),
                )

    def test_home_news_renders_image_url(self):
        with current_app.app_context():
            utils.makeOneCollection({"name_pt": "coleção falsa"})
            News(
                _id=uuid4().hex,
                title="Notícia com imagem",
                description="resumo da notícia",
                url="https://blog.scielo.org/blog/2020/01/29/random-url",
                language="pt_BR",
                is_public=True,
                publication_date=datetime(2024, 1, 15, 12, 0, 0),
                image_url="https://blog.scielo.org/wp-content/image.jpg",
            ).save()

            with self.client as c:
                response = c.get(
                    url_for("main.set_locale", lang_code="pt_BR"),
                    headers={"Referer": "/"},
                    follow_redirects=True,
                )

            html = response.data.decode("utf-8")
            self.assertStatus(response, 200)
            self.assertIn("Notícia com imagem", html)
            self.assertIn('src="https://blog.scielo.org/wp-content/image.jpg"', html)
            self.assertNotIn("img-post-blog-scielo-exemplo.jpg", html)

    def test_home_news_without_image_uses_fallback(self):
        with current_app.app_context():
            utils.makeOneCollection({"name_pt": "coleção falsa"})
            News(
                _id=uuid4().hex,
                title="Notícia sem imagem",
                description="resumo da notícia",
                url="https://blog.scielo.org/blog/2020/01/29/no-image",
                language="pt_BR",
                is_public=True,
                publication_date=datetime(2024, 1, 15, 12, 0, 0),
            ).save()

            with self.client as c:
                response = c.get(
                    url_for("main.set_locale", lang_code="pt_BR"),
                    headers={"Referer": "/"},
                    follow_redirects=True,
                )

            html = response.data.decode("utf-8")
            self.assertStatus(response, 200)
            self.assertIn("Notícia sem imagem", html)
            self.assertIn("img-post-blog-scielo-exemplo.jpg", html)

    def test_home_does_not_show_news_from_another_language(self):
        with current_app.app_context():
            utils.makeOneCollection(
                {
                    "name_pt": "coleção falsa",
                    "name_en": "dummy collection",
                }
            )
            News(
                _id=uuid4().hex,
                title="Notícia em português",
                description="resumo da notícia",
                url="https://blog.scielo.org/blog/2020/01/29/pt",
                language="pt_BR",
                is_public=True,
                publication_date=datetime(2024, 1, 15, 12, 0, 0),
                image_url="https://blog.scielo.org/wp-content/image.jpg",
            ).save()

            with self.client as c:
                response = c.get(
                    url_for("main.set_locale", lang_code="en"),
                    headers={"Referer": "/"},
                    follow_redirects=True,
                )

            html = response.data.decode("utf-8")
            self.assertStatus(response, 200)
            self.assertNotIn("Notícia em português", html)
            self.assertNotIn("https://blog.scielo.org/wp-content/image.jpg", html)
