# coding: utf-8
"""Unit tests for webapp.utils.i18n (100% line+branch coverage)."""

from unittest.mock import patch

from flask import current_app
from webapp.utils import i18n

from .base import BaseTestCase


class CanonicalInterfaceLangTests(BaseTestCase):
    def test_empty_returns_none(self):
        with current_app.test_request_context("/"):
            self.assertIsNone(i18n.canonical_interface_lang(None))
            self.assertIsNone(i18n.canonical_interface_lang(""))

    def test_exact_key(self):
        with current_app.test_request_context("/"):
            self.assertEqual(i18n.canonical_interface_lang("pt_BR"), "pt_BR")
            self.assertEqual(i18n.canonical_interface_lang("en"), "en")

    def test_hyphen_normalized_to_key(self):
        with current_app.test_request_context("/"):
            self.assertEqual(i18n.canonical_interface_lang("pt-BR"), "pt_BR")

    def test_case_insensitive_key(self):
        with current_app.test_request_context("/"):
            self.assertEqual(i18n.canonical_interface_lang("pt_br"), "pt_BR")
            self.assertEqual(i18n.canonical_interface_lang("EN"), "en")

    def test_primary_tag_alias(self):
        with current_app.test_request_context("/"):
            self.assertEqual(i18n.canonical_interface_lang("en-US"), "en")
            self.assertEqual(i18n.canonical_interface_lang("es_MX"), "es")
            self.assertEqual(i18n.canonical_interface_lang("pt"), "pt_BR")

    def test_unknown_code_returns_none(self):
        with current_app.test_request_context("/"):
            self.assertIsNone(i18n.canonical_interface_lang("fr"))
            self.assertIsNone(i18n.canonical_interface_lang("de-DE"))

    def test_empty_languages_config(self):
        with current_app.test_request_context("/"):
            previous = current_app.config["LANGUAGES"]
            current_app.config["LANGUAGES"] = {}
            try:
                self.assertIsNone(i18n.canonical_interface_lang("en"))
            finally:
                current_app.config["LANGUAGES"] = previous

    def test_primary_alias_not_in_languages(self):
        with current_app.test_request_context("/"):
            previous = current_app.config["LANGUAGES"]
            current_app.config["LANGUAGES"] = {"es": "Español"}
            try:
                # primary "en" maps to "en", but "en" is not in LANGUAGES
                self.assertIsNone(i18n.canonical_interface_lang("en-US"))
            finally:
                current_app.config["LANGUAGES"] = previous

    def test_languages_config_none_treated_as_empty(self):
        with current_app.test_request_context("/"):
            previous = current_app.config["LANGUAGES"]
            current_app.config["LANGUAGES"] = None
            try:
                self.assertIsNone(i18n.canonical_interface_lang("pt_BR"))
            finally:
                current_app.config["LANGUAGES"] = previous


class MatchAcceptLanguageTests(BaseTestCase):
    def test_empty_languages_returns_none(self):
        with current_app.test_request_context("/"):
            previous = current_app.config["LANGUAGES"]
            current_app.config["LANGUAGES"] = {}
            try:
                self.assertIsNone(i18n.match_accept_language())
            finally:
                current_app.config["LANGUAGES"] = previous

    def test_no_accept_match_returns_none(self):
        with current_app.test_request_context(
            "/", headers={"Accept-Language": "fr,de;q=0.8"}
        ):
            self.assertIsNone(i18n.match_accept_language())

    def test_match_returns_canonical(self):
        with current_app.test_request_context(
            "/", headers={"Accept-Language": "pt-BR,en;q=0.8"}
        ):
            self.assertEqual(i18n.match_accept_language(), "pt_BR")

    def test_best_match_unknown_falls_through_to_canonical(self):
        with current_app.test_request_context("/"):
            with patch(
                "webapp.utils.i18n.request.accept_languages"
            ) as mock_accept:
                mock_accept.best_match.return_value = "xx-YY"
                with patch(
                    "webapp.utils.i18n.canonical_interface_lang", return_value="en"
                ) as mock_canonical:
                    result = i18n.match_accept_language()
                    self.assertEqual(result, "en")
                    mock_canonical.assert_called_once_with("xx-YY")

    def test_best_match_unknown_and_canonical_none(self):
        with current_app.test_request_context("/"):
            with patch(
                "webapp.utils.i18n.request.accept_languages"
            ) as mock_accept:
                mock_accept.best_match.return_value = "zz"
                with patch(
                    "webapp.utils.i18n.canonical_interface_lang", return_value=None
                ):
                    self.assertIsNone(i18n.match_accept_language())

    def test_best_match_none(self):
        with current_app.test_request_context("/"):
            with patch(
                "webapp.utils.i18n.request.accept_languages"
            ) as mock_accept:
                mock_accept.best_match.return_value = None
                self.assertIsNone(i18n.match_accept_language())


class GetLocaleTests(BaseTestCase):
    def test_ilang_wins(self):
        with current_app.test_request_context("/?ilang=es"):
            self.assertEqual(i18n.get_locale(), "es")

    def test_accept_language_when_no_ilang(self):
        with current_app.test_request_context(
            "/", headers={"Accept-Language": "en"}
        ):
            self.assertEqual(i18n.get_locale(), "en")

    def test_default_when_no_match(self):
        with current_app.test_request_context(
            "/", headers={"Accept-Language": "fr"}
        ):
            self.assertEqual(
                i18n.get_locale(), current_app.config.get("BABEL_DEFAULT_LOCALE")
            )

    def test_default_when_no_request_context(self):
        self.assertEqual(
            i18n.get_locale(),
            current_app.config.get("BABEL_DEFAULT_LOCALE", "pt_BR"),
        )

    def test_default_fallback_when_config_missing_key(self):
        with current_app.test_request_context(
            "/", headers={"Accept-Language": "fr"}
        ):
            previous = current_app.config.pop("BABEL_DEFAULT_LOCALE", None)
            try:
                self.assertEqual(i18n.get_locale(), "pt_BR")
            finally:
                if previous is not None:
                    current_app.config["BABEL_DEFAULT_LOCALE"] = previous


class BuildIlangUrlTests(BaseTestCase):
    def test_replaces_ilang_and_keeps_other_args(self):
        with current_app.test_request_context("/journals/?foo=1&ilang=pt_BR"):
            url = i18n.build_ilang_url("en")
            self.assertTrue(url.startswith("/journals/?"))
            self.assertIn("foo=1", url)
            self.assertIn("ilang=en", url)

    def test_adds_ilang_when_query_empty(self):
        with current_app.test_request_context("/about/"):
            self.assertEqual(i18n.build_ilang_url("es"), "/about/?ilang=es")


class IsStaticEndpointTests(BaseTestCase):
    def test_falsy_endpoint_is_not_static(self):
        self.assertFalse(i18n._is_static_endpoint(None))
        self.assertFalse(i18n._is_static_endpoint(""))

    def test_static_and_blueprint_static(self):
        self.assertTrue(i18n._is_static_endpoint("static"))
        self.assertTrue(i18n._is_static_endpoint("admin.static"))
        self.assertFalse(i18n._is_static_endpoint("main.index"))


class UrlForWithIlangTests(BaseTestCase):
    def test_injects_ilang_from_g_lang(self):
        with current_app.test_request_context("/?ilang=es"):
            from flask import g

            g.lang = "es"
            url = i18n.url_for_with_ilang("main.index")
            self.assertIn("ilang=es", url)

    def test_respects_explicit_ilang(self):
        with current_app.test_request_context("/?ilang=es"):
            from flask import g

            g.lang = "es"
            url = i18n.url_for_with_ilang("main.index", ilang="en")
            self.assertIn("ilang=en", url)
            self.assertNotIn("ilang=es", url)

    def test_skips_static(self):
        with current_app.test_request_context("/"):
            from flask import g

            g.lang = "en"
            url = i18n.url_for_with_ilang("static", filename="css/bootstrap.css")
            self.assertNotIn("ilang=", url)

    def test_combines_with_other_query_kwargs(self):
        with current_app.test_request_context("/"):
            from flask import g

            g.lang = "en"
            url = i18n.url_for_with_ilang("main.collection_list", status="current")
            self.assertIn("status=current", url)
            self.assertIn("ilang=en", url)
            self.assertEqual(url.count("?"), 1)


class InjectIlangIntoUrlTests(BaseTestCase):
    def test_none_or_empty_url_returns_none(self):
        self.assertIsNone(i18n.inject_ilang_into_url(None, "en"))
        self.assertIsNone(i18n.inject_ilang_into_url("", "en"))

    def test_injects_ilang_preserving_path_and_query(self):
        result = i18n.inject_ilang_into_url("/about/?x=1", "en")
        self.assertEqual(result, "/about/?x=1&ilang=en")

    def test_replaces_existing_ilang(self):
        result = i18n.inject_ilang_into_url("/?ilang=pt_BR", "es")
        self.assertEqual(result, "/?ilang=es")

    def test_explicit_fragment_overrides(self):
        result = i18n.inject_ilang_into_url("/about/#old", "en", fragment="new")
        self.assertEqual(result, "/about/?ilang=en#new")

    def test_keeps_existing_fragment_when_fragment_arg_is_none(self):
        result = i18n.inject_ilang_into_url("/about/#keep", "en", fragment=None)
        self.assertEqual(result, "/about/?ilang=en#keep")

    def test_empty_fragment_arg_clears_fragment(self):
        result = i18n.inject_ilang_into_url("/about/#gone", "en", fragment="")
        self.assertEqual(result, "/about/?ilang=en")
