# coding: utf-8
from unittest.mock import patch

from flask import current_app
from webapp.utils import caching

from .base import BaseTestCase


class CachingUtilsTestCase(BaseTestCase):
    def test_cache_key_format_without_qs(self):
        self.assertEqual(
            caching._cache_key_format("pt_BR", "/journals/"),
            "/LANG=pt_BR/PATH=/journals/",
        )

    def test_cache_key_format_with_qs(self):
        self.assertEqual(
            caching._cache_key_format("en", "/search/", "abc123"),
            "/LANG=en/PATH=/search/?QS=abc123",
        )

    def test_make_querystring_hash_is_stable(self):
        with self.client as client:
            client.get("/?b=2&a=1")
            h1 = caching._make_querystring_hash()
            client.get("/?a=1&b=2")
            h2 = caching._make_querystring_hash()
            self.assertEqual(h1, h2)
            self.assertEqual(len(h1), 32)

    def test_cache_key_with_lang_uses_session_or_default(self):
        with self.client as client:
            with client.session_transaction() as sess:
                sess.clear()
            client.get("/")
            default_lang = current_app.config.get("BABEL_DEFAULT_LOCALE")
            key = caching.cache_key_with_lang()
            self.assertIn("PATH=/", key)
            self.assertIn("LANG=%s" % default_lang, key)

            with client.session_transaction() as sess:
                sess["lang"] = "es"
            client.get("/journals/")
            key_es = caching.cache_key_with_lang()
            self.assertIn("LANG=es", key_es)
            self.assertIn("PATH=/journals/", key_es)

    def test_cache_key_with_lang_with_qs(self):
        with self.client as client:
            with client.session_transaction() as sess:
                sess["lang"] = "en"
            client.get("/journals/download/alpha/csv/?query=saude")
            key = caching.cache_key_with_lang_with_qs()
            self.assertIn("LANG=en", key)
            self.assertIn("QS=", key)
            self.assertIn("PATH=", key)
