# coding: utf-8

from webapp.config.lang_names import display_original_lang_name, get_original_lang_name
from webapp.main.custom_filters import trans_alpha2

from .base import BaseTestCase


class LangNamesTestCase(BaseTestCase):
    def test_get_original_lang_name(self):
        self.assertEqual(get_original_lang_name("pt"), "Português")
        self.assertEqual(get_original_lang_name("en"), "English")
        self.assertEqual(get_original_lang_name("es"), "Español")
        self.assertEqual(get_original_lang_name("fr"), "français, langue française")
        self.assertEqual(get_original_lang_name("de"), "Deutsch")
        self.assertEqual(get_original_lang_name("it"), "Italiano")
        self.assertEqual(get_original_lang_name("zh"), "中文 (Zhōngwén), 汉语, 漢語")
        self.assertEqual(get_original_lang_name("ar"), "العربية")

    def test_get_original_lang_name_inexisting(self):
        self.assertEqual(get_original_lang_name("bla"), None)

    def test_display_original_lang_name(self):
        self.assertEqual(display_original_lang_name("pt"), "Português")
        self.assertEqual(display_original_lang_name("en"), "English")
        self.assertEqual(display_original_lang_name("es"), "Español")
        self.assertEqual(display_original_lang_name("fr"), "Français")
        self.assertEqual(display_original_lang_name("de"), "Deutsch")
        self.assertEqual(display_original_lang_name("it"), "Italiano")
        self.assertEqual(display_original_lang_name("zh"), "中文 (zhōngwén)")
        self.assertEqual(display_original_lang_name("ar"), "العربية")

    def test_display_original_lang_name_inexisting(self):
        self.assertEqual(display_original_lang_name("bla"), "bla")


class TransAlpha2TestCase(BaseTestCase):
    def test_trans_alpha2_known_languages(self):
        """Languages in ISO3166_ALPHA2 should return translated names."""
        result_pt = str(trans_alpha2("pt"))
        result_en = str(trans_alpha2("en"))
        result_es = str(trans_alpha2("es"))
        result_fr = str(trans_alpha2("fr"))
        result_de = str(trans_alpha2("de"))
        result_it = str(trans_alpha2("it"))
        result_ru = str(trans_alpha2("ru"))
        self.assertEqual(result_pt, "Português")
        self.assertEqual(result_en, "Inglês")
        self.assertEqual(result_es, "Espanhol")
        self.assertEqual(result_fr, "Francês")
        self.assertEqual(result_de, "Alemão")
        self.assertEqual(result_it, "Italiano")
        self.assertEqual(result_ru, "Russo")

    def test_trans_alpha2_fallback_to_lang_names(self):
        """Languages not in ISO3166_ALPHA2 but in LANG_NAMES should return ISO English name."""
        self.assertEqual(trans_alpha2("ja"), "Japanese")
        self.assertEqual(trans_alpha2("ko"), "Korean")
        self.assertEqual(trans_alpha2("pl"), "Polish")
        self.assertEqual(trans_alpha2("sv"), "Swedish")
        self.assertEqual(trans_alpha2("tr"), "Turkish")

    def test_trans_alpha2_fallback_with_comma(self):
        """Languages with comma-separated names should return only the first name."""
        self.assertEqual(trans_alpha2("nl"), "Dutch")
        self.assertEqual(trans_alpha2("sk"), "Slovak")

    def test_trans_alpha2_unknown_code(self):
        """Unknown language codes should return the code itself."""
        self.assertEqual(trans_alpha2("bla"), "bla")
        self.assertEqual(trans_alpha2("xyz"), "xyz")
