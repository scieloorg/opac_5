# coding: utf-8
"""Interface locale via ``ilang`` query param and Accept-Language (issue #438)."""

from flask import current_app, g, url_for

from . import utils
from .base import BaseTestCase


class InterfaceLocaleTestCase(BaseTestCase):
    def setUp(self):
        super(InterfaceLocaleTestCase, self).setUp()
        utils.makeOneCollection()

    def test_ilang_sets_interface_language(self):
        for lang in ("en", "es", "pt_BR"):
            with self.subTest(lang=lang):
                with self.client as client:
                    response = client.get("/?ilang=%s" % lang)
                    self.assertStatus(response, 200)
                    self.assertEqual(g.lang, lang)

    def test_ilang_invalid_falls_back_to_accept_language_or_default(self):
        with self.client as client:
            response = client.get(
                "/?ilang=fr",
                headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            self.assertStatus(response, 200)
            self.assertEqual(g.lang, "en")

    def test_accept_language_en(self):
        with self.client as client:
            response = client.get("/", headers={"Accept-Language": "en"})
            self.assertStatus(response, 200)
            self.assertEqual(g.lang, "en")

    def test_accept_language_en_US(self):
        with self.client as client:
            response = client.get("/", headers={"Accept-Language": "en-US"})
            self.assertStatus(response, 200)
            self.assertEqual(g.lang, "en")

    def test_accept_language_es(self):
        with self.client as client:
            response = client.get("/", headers={"Accept-Language": "es"})
            self.assertStatus(response, 200)
            self.assertEqual(g.lang, "es")

    def test_accept_language_es_ES(self):
        with self.client as client:
            response = client.get("/", headers={"Accept-Language": "es-ES"})
            self.assertStatus(response, 200)
            self.assertEqual(g.lang, "es")

    def test_accept_language_pt_BR(self):
        with self.client as client:
            response = client.get("/", headers={"Accept-Language": "pt-BR"})
            self.assertStatus(response, 200)
            self.assertEqual(g.lang, "pt_BR")

    def test_accept_language_pt(self):
        with self.client as client:
            response = client.get("/", headers={"Accept-Language": "pt"})
            self.assertStatus(response, 200)
            self.assertEqual(g.lang, "pt_BR")

    def test_accept_language_q_values_prefers_supported(self):
        with self.client as client:
            response = client.get("/", headers={"Accept-Language": "fr,en;q=0.9"})
            self.assertStatus(response, 200)
            self.assertEqual(g.lang, "en")

    def test_unsupported_accept_language_defaults_pt_BR(self):
        with self.client as client:
            response = client.get("/", headers={"Accept-Language": "fr,de;q=0.8"})
            self.assertStatus(response, 200)
            self.assertEqual(g.lang, "pt_BR")

    def test_ilang_overrides_accept_language(self):
        with self.client as client:
            response = client.get(
                "/?ilang=es",
                headers={"Accept-Language": "en"},
            )
            self.assertStatus(response, 200)
            self.assertEqual(g.lang, "es")

    def test_no_active_language_cookie_set(self):
        with self.client as client:
            response = client.get("/?ilang=en")
            self.assertStatus(response, 200)
            set_cookie = response.headers.getlist("Set-Cookie")
            language_cookies = [
                c for c in set_cookie if c.lower().startswith("language=")
            ]
            for cookie in language_cookies:
                # Legacy clear may appear as empty/expired; never an active locale.
                self.assertNotIn("language=en", cookie)
                self.assertNotIn("language=pt_BR", cookie)
                self.assertNotIn("language=es", cookie)

    def test_clears_legacy_language_cookie_when_present(self):
        with self.client as client:
            client.set_cookie("language", "pt_BR")
            response = client.get("/")
            self.assertStatus(response, 200)
            set_cookie = "; ".join(response.headers.getlist("Set-Cookie"))
            self.assertIn("language=", set_cookie.lower())

    def test_vary_accept_language_without_ilang(self):
        with self.client as client:
            response = client.get("/", headers={"Accept-Language": "en"})
            self.assertStatus(response, 200)
            self.assertIn("Accept-Language", response.headers.get("Vary", ""))

    def test_switcher_links_use_ilang_query(self):
        with self.client as client:
            response = client.get("/?ilang=pt_BR")
            self.assertStatus(response, 200)
            html = response.data.decode("utf-8")
            self.assertIn("ilang=en", html)
            self.assertIn("ilang=es", html)
            self.assertNotIn('href="/set_locale/', html)

    def test_set_locale_redirects_with_ilang(self):
        with self.client as client:
            response = client.get(
                url_for("main.set_locale", lang_code="en"),
                headers={"Referer": "/journals/alpha"},
                follow_redirects=False,
            )
            self.assertEqual(response.status_code, 302)
            self.assertIn("ilang=en", response.location)
            self.assertIn("/journals/alpha", response.location)
            from flask import session

            self.assertNotIn("lang", session)

    def test_set_locale_without_referrer_redirects_home_with_ilang(self):
        with self.client as client:
            response = client.get(
                url_for("main.set_locale", lang_code="es"),
                follow_redirects=False,
            )
            self.assertEqual(response.status_code, 302)
            self.assertIn("ilang=es", response.location)

    def test_set_locale_invalid_lang_returns_400(self):
        with self.client as client:
            response = client.get(url_for("main.set_locale", lang_code="en_US"))
            self.assertEqual(response.status_code, 400)

    def test_url_path_unchanged_when_switching_language(self):
        with self.client as client:
            response = client.get("/?foo=1&ilang=pt_BR")
            self.assertStatus(response, 200)
            html = response.data.decode("utf-8").replace("&amp;", "&")
            # Switcher keeps path and replaces only ilang (other QS preserved).
            self.assertIn("/?foo=1&ilang=en", html)
            self.assertIn("/?foo=1&ilang=es", html)

    def test_ilang_hyphen_and_case_variants(self):
        with self.client as client:
            response = client.get("/?ilang=pt-BR")
            self.assertStatus(response, 200)
            self.assertEqual(g.lang, "pt_BR")

            response = client.get("/?ilang=en-US")
            self.assertStatus(response, 200)
            self.assertEqual(g.lang, "en")

    def test_no_vary_accept_language_when_ilang_valid(self):
        with self.client as client:
            response = client.get("/?ilang=en")
            self.assertStatus(response, 200)
            self.assertNotIn("Accept-Language", response.headers.get("Vary", ""))

    def test_vary_appends_when_header_already_present(self):
        from webapp.main.views import add_header
        from flask import make_response

        with current_app.test_request_context("/"):
            response = make_response("ok")
            response.headers["Vary"] = "Accept-Encoding"
            result = add_header(response)
            self.assertEqual(result.headers["Vary"], "Accept-Encoding, Accept-Language")

    def test_vary_does_not_duplicate_accept_language(self):
        from webapp.main.views import add_header
        from flask import make_response

        with current_app.test_request_context("/"):
            response = make_response("ok")
            response.headers["Vary"] = "Accept-Language"
            result = add_header(response)
            self.assertEqual(result.headers["Vary"], "Accept-Language")

    def test_url_for_ilang_template_global(self):
        from webapp.main.views import url_for_ilang

        with current_app.test_request_context("/journals/?q=1"):
            self.assertEqual(url_for_ilang("es"), "/journals/?q=1&ilang=es")

    def test_nav_links_preserve_ilang(self):
        with self.client as client:
            response = client.get("/?ilang=en")
            self.assertStatus(response, 200)
            html = response.data.decode("utf-8").replace("&amp;", "&")
            self.assertIn("ilang=en", html)
            # Lista alfabética: status e ilang na mesma query (um único ?)
            self.assertRegex(
                html,
                r'href="[^"]*journals/alpha\?[^"]*status=current[^"]*ilang=en[^"]*"'
                r'|href="[^"]*journals/alpha\?[^"]*ilang=en[^"]*status=current[^"]*"',
            )
            self.assertNotRegex(
                html,
                r'href="[^"]*journals/alpha[^"]*\?[^"]*\?',
            )

    def test_collection_list_links_preserve_ilang(self):
        with self.client as client:
            response = client.get("/journals/alpha?ilang=es&status=current")
            self.assertStatus(response, 200)
            html = response.data.decode("utf-8").replace("&amp;", "&")
            self.assertRegex(
                html,
                r'href="[^"]*journals/thematic\?[^"]*status=current[^"]*ilang=es[^"]*"'
                r'|href="[^"]*journals/thematic\?[^"]*ilang=es[^"]*status=current[^"]*"',
            )
            # Home logo / index also carries ilang
            self.assertIn("ilang=es", html)
            self.assertRegex(html, r'href="/\?ilang=es"|href="[^"]*/\?ilang=es"')

    def test_switcher_still_changes_ilang_independently(self):
        with self.client as client:
            response = client.get("/?ilang=en")
            self.assertStatus(response, 200)
            html = response.data.decode("utf-8").replace("&amp;", "&")
            self.assertIn("/?ilang=es", html)
            self.assertIn("/?ilang=pt_BR", html)

    def test_does_not_clear_language_cookie_when_absent(self):
        with self.client as client:
            response = client.get("/")
            self.assertStatus(response, 200)
            set_cookie = "; ".join(response.headers.getlist("Set-Cookie"))
            # Must not emit an active language cookie; expire only if client sent one.
            self.assertNotIn("language=pt_BR", set_cookie)
            self.assertNotIn("language=en", set_cookie)
