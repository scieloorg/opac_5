# coding: utf-8

from flask import current_app, g, url_for

from . import utils
from .base import BaseTestCase


class HeaderTestCase(BaseTestCase):
    def test_current_language_when_set_pt_br(self):
        """
        Com ``ilang=pt_BR``, o switcher oferece links para en e es (não para pt_BR).
        """

        with current_app.app_context():
            utils.makeOneCollection()
            with self.client as c:
                response = c.get("/?ilang=pt_BR")
                self.assertStatus(response, 200)

                self.assertTemplateUsed("collection/index.html")
                self.assertEqual(g.lang, "pt_BR")
                html = response.data.decode("utf-8").replace("&amp;", "&")
                self.assertIn("ilang=en", html)
                self.assertIn("ilang=es", html)
                # Current language is shown as label, not as a switcher link.
                self.assertNotIn('href="/?ilang=pt_BR"', html)

    def test_current_language_when_set_en(self):
        """
        Com ``ilang=en``, o switcher oferece links para pt_BR e es.
        """

        with current_app.app_context():
            utils.makeOneCollection()
            with self.client as c:
                response = c.get("/?ilang=en")
                self.assertStatus(response, 200)

                self.assertTemplateUsed("collection/index.html")
                self.assertEqual(g.lang, "en")
                html = response.data.decode("utf-8").replace("&amp;", "&")
                self.assertIn("ilang=pt_BR", html)
                self.assertIn("ilang=es", html)
                self.assertNotIn('href="/?ilang=en"', html)

    def test_current_language_when_set_es(self):
        """
        Com ``ilang=es``, o switcher mostra links para pt_BR e en.
        """

        with current_app.app_context():
            utils.makeOneCollection()
            with self.client as c:
                response = c.get("/?ilang=es")
                self.assertStatus(response, 200)

                self.assertTemplateUsed("collection/index.html")
                self.assertEqual(g.lang, "es")
                html = response.data.decode("utf-8").replace("&amp;", "&")
                self.assertIn("ilang=pt_BR", html)
                self.assertIn("ilang=en", html)
                self.assertNotIn('href="/?ilang=es"', html)
