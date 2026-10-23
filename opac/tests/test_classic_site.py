# coding: utf-8
from unittest.mock import patch

import requests
from flask import current_app, url_for

from webapp.utils.classic_site import (
    classic_article_url,
    configured_search_host,
    previous_website_base_url,
    response_confirms_classic_article,
)

from . import utils
from .base import BaseTestCase


class ClassicSiteTestCase(BaseTestCase):
    def test_previous_website_base_url_normalizes_scheme(self):
        self.assertIsNone(previous_website_base_url(""))
        self.assertIsNone(previous_website_base_url("   "))
        self.assertEqual(
            "https://old.example.org",
            previous_website_base_url("old.example.org"),
        )
        self.assertEqual(
            "https://old.example.org",
            previous_website_base_url("https://old.example.org/"),
        )
        self.assertEqual(
            "http://old.example.org",
            previous_website_base_url("http://old.example.org"),
        )
        self.assertEqual(
            "https://old.example.org",
            previous_website_base_url("//old.example.org"),
        )

    def test_classic_article_url_quotes_pid(self):
        self.assertIsNone(classic_article_url("", "https://old.example.org"))
        self.assertIsNone(classic_article_url("S0102", ""))
        self.assertEqual(
            "https://old.example.org/scielo.php?script=sci_arttext&pid=S0102-311X",
            classic_article_url("S0102-311X", "old.example.org"),
        )
        self.assertEqual(
            "https://old.example.org/scielo.php?script=sci_arttext&pid=S0102%26X",
            classic_article_url("S0102&X", "https://old.example.org"),
        )

    def test_response_confirms_classic_article(self):
        article = '<meta name="citation_title" content="Title">'
        self.assertTrue(response_confirms_classic_article(200, article))
        self.assertFalse(response_confirms_classic_article(404, article))
        self.assertFalse(response_confirms_classic_article(200, "<html></html>"))
        self.assertFalse(
            response_confirms_classic_article(
                200, article + " Documento não encontrado"
            )
        )
        self.assertFalse(
            response_confirms_classic_article(200, "Artigo não encontrado")
        )

    def test_configured_search_host(self):
        previous = current_app.config.get("URL_SEARCH")
        try:
            current_app.config["URL_SEARCH"] = "//search.scielo.org/"
            self.assertEqual("search.scielo.org", configured_search_host())
            current_app.config["URL_SEARCH"] = "https://search.example.org/search"
            self.assertEqual("search.example.org", configured_search_host())
        finally:
            current_app.config["URL_SEARCH"] = previous

    def test_home_uses_backend_previous_website_url(self):
        utils.makeOneCollection()
        previous_uri = current_app.config.get("PREVIOUS_WEBSITE_URI")
        previous_alert = current_app.config.get("ALERT_MSG")
        current_app.config["PREVIOUS_WEBSITE_URI"] = "old.example.org"
        current_app.config["ALERT_MSG"] = True
        try:
            response = self.client.get(url_for("main.index"))
            body = response.data.decode("utf-8")
            self.assertStatus(response, 200)
            self.assertIn('href="https://old.example.org"', body)
            self.assertIn("Acessar versão anterior", body)
            self.assertNotIn('href="old.example.org"', body)
        finally:
            current_app.config["PREVIOUS_WEBSITE_URI"] = previous_uri
            current_app.config["ALERT_MSG"] = previous_alert

    def test_missing_previous_website_uri_logs_and_returns_404(self):
        utils.makeOneCollection()
        previous = current_app.config.get("PREVIOUS_WEBSITE_URI")
        current_app.config["PREVIOUS_WEBSITE_URI"] = ""
        try:
            url = "%s?script=sci_arttext&pid=%s" % (
                url_for("main.router_legacy"),
                "S0000-00000000000000000",
            )
            with self.assertLogs("webapp.main.views", level="WARNING") as logs:
                response = self.client.get(url)
            body = response.data.decode("utf-8")
            self.assertStatus(response, 404)
            self.assertIn("Artigo não encontrado", body)
            self.assertNotIn("scielo.php?script=sci_arttext", body)
            self.assertTrue(
                any("PREVIOUS_WEBSITE_URI indefinida" in message for message in logs.output)
            )
        finally:
            current_app.config["PREVIOUS_WEBSITE_URI"] = previous

    def test_classic_lookup_failure_returns_404(self):
        utils.makeOneCollection()
        previous = current_app.config.get("PREVIOUS_WEBSITE_URI")
        current_app.config["PREVIOUS_WEBSITE_URI"] = "https://old.example.org"
        try:
            url = "%s?script=sci_abstract&pid=%s" % (
                url_for("main.router_legacy"),
                "S0000-00000000000000001",
            )
            with patch(
                "webapp.main.views.fetch_classic_article",
                side_effect=requests.Timeout("slow"),
            ):
                with self.assertLogs("webapp.main.views", level="WARNING") as logs:
                    response = self.client.get(url)
            self.assertStatus(response, 404)
            self.assertIn("Artigo não encontrado", response.data.decode("utf-8"))
            self.assertTrue(any("Falha ao consultar" in message for message in logs.output))
        finally:
            current_app.config["PREVIOUS_WEBSITE_URI"] = previous
