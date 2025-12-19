# coding: utf-8
from webapp.main.custom_filters import get_absolute_url

from .base import BaseTestCase


class CustomFiltersTestCase(BaseTestCase):
    """Test cases for custom Jinja2 filters in webapp.main.custom_filters"""

    def test_get_absolute_url_with_absolute_http_url(self):
        """Test that absolute HTTP URLs are returned as-is"""
        url = "http://example.com/logo.png"
        base_url = "http://scielo.do/"
        result = get_absolute_url(url, base_url)
        self.assertEqual(result, "http://example.com/logo.png")

    def test_get_absolute_url_with_absolute_https_url(self):
        """Test that absolute HTTPS URLs are returned as-is"""
        url = "https://example.com/logo.png"
        base_url = "http://scielo.do/"
        result = get_absolute_url(url, base_url)
        self.assertEqual(result, "https://example.com/logo.png")

    def test_get_absolute_url_with_relative_url_with_slash(self):
        """Test that relative URLs with leading slash are concatenated correctly"""
        url = "/media/logo.png"
        base_url = "http://scielo.do/"
        result = get_absolute_url(url, base_url)
        self.assertEqual(result, "http://scielo.do/media/logo.png")

    def test_get_absolute_url_with_relative_url_without_slash(self):
        """Test that relative URLs without leading slash are concatenated correctly"""
        url = "media/logo.png"
        base_url = "http://scielo.do/"
        result = get_absolute_url(url, base_url)
        self.assertEqual(result, "http://scielo.do/media/logo.png")

    def test_get_absolute_url_with_empty_url(self):
        """Test that empty URLs return empty string"""
        url = ""
        base_url = "http://scielo.do/"
        result = get_absolute_url(url, base_url)
        self.assertEqual(result, "")

    def test_get_absolute_url_with_none_url(self):
        """Test that None URLs return empty string"""
        url = None
        base_url = "http://scielo.do/"
        result = get_absolute_url(url, base_url)
        self.assertEqual(result, "")

    def test_get_absolute_url_with_empty_base_url(self):
        """Test that relative URLs with empty base_url work"""
        url = "/media/logo.png"
        base_url = ""
        result = get_absolute_url(url, base_url)
        self.assertEqual(result, "media/logo.png")
