# coding: utf-8

import re

from flask import current_app, g

from . import utils
from .base import BaseTestCase


def _switcher_dropdown_html(html):
    """Extract the language switcher dropdown menu markup."""
    match = re.search(
        r'<ul class="dropdown-menu dropdown-menu-end">(.*?)</ul>',
        html,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError("Language switcher dropdown not found in HTML")
    return match.group(1)


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
                switcher = _switcher_dropdown_html(html)
                self.assertIn('href="/?ilang=en"', switcher)
                self.assertIn('href="/?ilang=es"', switcher)
                # Current language is shown as label, not as a switcher link.
                self.assertNotIn('href="/?ilang=pt_BR"', switcher)
                # Nav/home links still keep the current interface language.
                self.assertIn('href="/?ilang=pt_BR"', html)

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
                switcher = _switcher_dropdown_html(html)
                self.assertIn('href="/?ilang=pt_BR"', switcher)
                self.assertIn('href="/?ilang=es"', switcher)
                self.assertNotIn('href="/?ilang=en"', switcher)
                self.assertIn('href="/?ilang=en"', html)

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
                switcher = _switcher_dropdown_html(html)
                self.assertIn('href="/?ilang=pt_BR"', switcher)
                self.assertIn('href="/?ilang=en"', switcher)
                self.assertNotIn('href="/?ilang=es"', switcher)
                self.assertIn('href="/?ilang=es"', html)
