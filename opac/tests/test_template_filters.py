# coding: utf-8
import datetime
import unittest

from flask import current_app

from .base import BaseTestCase


class TestMakeAbsoluteUrl(BaseTestCase):
    """Testes para o filtro make_absolute_url"""

    def setUp(self):
        super().setUp()
        from webapp.main.custom_filters import make_absolute_url

        self.make_absolute_url = make_absolute_url

    def test_none_returns_empty_string(self):
        """None deve retornar string vazia"""
        self.assertEqual(self.make_absolute_url(None), '')

    def test_empty_string_returns_empty_string(self):
        """String vazia deve retornar string vazia"""
        self.assertEqual(self.make_absolute_url(''), '')

    def test_absolute_http_url_unchanged(self):
        """URL absoluta HTTP deve ser retornada sem modificação"""
        url = 'http://example.com/logo.png'
        self.assertEqual(self.make_absolute_url(url), url)
        self.assertEqual(self.make_absolute_url(url, 'http://scielo.do'), url)

    def test_absolute_https_url_unchanged(self):
        """URL absoluta HTTPS deve ser retornada sem modificação"""
        url = 'https://cdn.example.com/images/logo.png'
        self.assertEqual(self.make_absolute_url(url), url)
        self.assertEqual(self.make_absolute_url(url, 'http://scielo.do'), url)

    def test_relative_url_with_leading_slash(self):
        """URL relativa com barra inicial deve ser concatenada corretamente"""
        result = self.make_absolute_url('/media/logo.png', 'http://scielo.do')
        self.assertEqual(result, 'http://scielo.do/media/logo.png')

    def test_relative_url_without_leading_slash(self):
        """URL relativa sem barra inicial deve ser concatenada corretamente"""
        result = self.make_absolute_url('media/logo.png', 'http://scielo.do')
        self.assertEqual(result, 'http://scielo.do/media/logo.png')

    def test_base_url_with_trailing_slash(self):
        """base_url com barra final não deve gerar barras duplicadas"""
        result = self.make_absolute_url('/media/logo.png', 'http://scielo.do/')
        self.assertEqual(result, 'http://scielo.do/media/logo.png')

    def test_no_base_url_returns_cleaned_url(self):
        """Sem base_url deve retornar URL limpa (sem barra inicial)"""
        result = self.make_absolute_url('/media/logo.png')
        self.assertEqual(result, 'media/logo.png')

        result = self.make_absolute_url('media/logo.png')
        self.assertEqual(result, 'media/logo.png')

    def test_complex_relative_path(self):
        """Caminhos relativos complexos devem funcionar"""
        result = self.make_absolute_url('/static/images/journals/logo-v2.png', 'https://scielo.br')
        self.assertEqual(result, 'https://scielo.br/static/images/journals/logo-v2.png')

    def test_empty_base_url_returns_relative_path(self):
        """base_url vazio deve retornar apenas a URL relativa limpa"""
        result = self.make_absolute_url('media/logo.png', '')
        self.assertEqual(result, 'media/logo.png')


class TestTransAlpha2(BaseTestCase):
    def setUp(self):
        super().setUp()
        from webapp.main.custom_filters import trans_alpha2

        self.trans_alpha2 = trans_alpha2

    def test_known_language_code(self):
        from webapp import choices

        self.assertEqual(
            self.trans_alpha2("en"),
            choices.ISO3166_ALPHA2["en"],
        )

    def test_unknown_language_code(self):
        self.assertEqual(self.trans_alpha2("zz"), "zz")

    def test_none_value(self):
        self.assertIsNone(self.trans_alpha2(None))

    def test_empty_value(self):
        self.assertEqual(self.trans_alpha2(""), "")


class TestDatetimeFilter(BaseTestCase):
    def setUp(self):
        super().setUp()
        from webapp.main.custom_filters import datetimefilter

        self.datetimefilter = datetimefilter
        self.utc_value = datetime.datetime(
            2021, 3, 10, 15, 45, tzinfo=datetime.timezone.utc
        )

    def test_custom_format(self):
        with current_app.app_context():
            result = self.datetimefilter(self.utc_value, "%d/%m/%Y")
        self.assertRegex(result, r"^\d{2}/\d{2}/\d{4}$")

    def test_default_format(self):
        with current_app.app_context():
            result = self.datetimefilter(self.utc_value)
        self.assertRegex(result, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")

    def test_none_raises_attribute_error(self):
        with current_app.app_context():
            with self.assertRaises(AttributeError):
                self.datetimefilter(None)


if __name__ == '__main__':
    unittest.main()