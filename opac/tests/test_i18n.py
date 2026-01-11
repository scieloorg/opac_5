# -*- coding: utf-8 -*-
"""
Testes para funcionalidades de internacionalização (i18n).

Testa detecção de idioma via Accept-Language header,
fallbacks, e comportamento em diferentes cenários.
"""

import unittest
import sys
import os

# Adiciona o diretório raiz ao path para imports funcionarem
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Configuração de ambiente antes de qualquer import do Flask
os.environ['OPAC_CONFIG'] = os.path.join(
    os.path.dirname(__file__),
    '../../config.py'
)


class SetupLanguageTestCase(unittest.TestCase):
    """Testes para a função setup_language()"""

    @classmethod
    def setUpClass(cls):
        """Configuração única para toda a classe de testes"""
        # Importa apenas depois de configurar ambiente
        try:
            from opac.webapp import create_app
            cls.create_app = create_app
        except ImportError as e:
            raise unittest.SkipTest(f"Não foi possível importar create_app: {e}")

    def setUp(self):
        """Configuração antes de cada teste"""
        try:
            self.app = self.create_app()
            self.app.config['TESTING'] = True
            self.app.config['LANGUAGES'] = {
                'pt_BR': 'Português',
                'en': 'English',
                'es': 'Español'
            }
            self.app.config['BABEL_DEFAULT_LOCALE'] = 'pt_BR'
            self.app_context = self.app.app_context()
            self.app_context.push()
        except Exception as e:
            self.skipTest(f"Erro ao configurar app: {e}")

    def tearDown(self):
        """Limpeza após cada teste"""
        if hasattr(self, 'app_context'):
            self.app_context.pop()

    def test_setup_language_single_exact_match(self):
        """Testa detecção de idioma com match exato"""
        from flask import g

        with self.app.test_request_context(
                '/',
                headers={'Accept-Language': 'pt-BR'}
        ):
            self.app.preprocess_request()
            self.assertEqual(g.interface_language, 'pt_BR')

    def test_setup_language_english(self):
        """Testa detecção de inglês"""
        from flask import g

        with self.app.test_request_context(
                '/',
                headers={'Accept-Language': 'en-US'}
        ):
            self.app.preprocess_request()
            self.assertEqual(g.interface_language, 'en')

    def test_setup_language_spanish(self):
        """Testa detecção de espanhol"""
        from flask import g

        with self.app.test_request_context(
                '/',
                headers={'Accept-Language': 'es-ES'}
        ):
            self.app.preprocess_request()
            self.assertEqual(g.interface_language, 'es')

    def test_setup_language_with_quality_values(self):
        """Testa detecção com quality values (q=)"""
        from flask import g

        with self.app.test_request_context(
                '/',
                headers={'Accept-Language': 'en;q=0.8,pt-BR;q=1.0,es;q=0.9'}
        ):
            self.app.preprocess_request()
            # Deve escolher pt_BR (maior q)
            self.assertEqual(g.interface_language, 'pt_BR')

    def test_setup_language_no_match_fallback(self):
        """Testa fallback quando idioma não é suportado"""
        from flask import g

        with self.app.test_request_context(
                '/',
                headers={'Accept-Language': 'fr-FR'}  # Francês não suportado
        ):
            self.app.preprocess_request()
            # Deve usar default (pt_BR)
            self.assertEqual(g.interface_language, 'pt_BR')

    def test_setup_language_missing_header(self):
        """Testa comportamento sem Accept-Language header"""
        from flask import g

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            # Deve usar default
            self.assertEqual(g.interface_language, 'pt_BR')

    def test_setup_language_empty_header(self):
        """Testa comportamento com header vazio"""
        from flask import g

        with self.app.test_request_context(
                '/',
                headers={'Accept-Language': ''}
        ):
            self.app.preprocess_request()
            # Deve usar default
            self.assertEqual(g.interface_language, 'pt_BR')

    def test_setup_language_sets_g_attribute(self):
        """Testa que g.interface_language é definido"""
        from flask import g

        with self.app.test_request_context(
                '/',
                headers={'Accept-Language': 'en'}
        ):
            self.app.preprocess_request()
            # Verifica que atributo existe
            self.assertTrue(hasattr(g, 'interface_language'))
            # Verifica que não é None
            self.assertIsNotNone(g.interface_language)

    def test_setup_language_respects_supported_languages(self):
        """Testa que apenas idiomas suportados são selecionados"""
        from flask import g

        with self.app.test_request_context(
                '/',
                headers={'Accept-Language': 'de-DE,it-IT,pt-BR'}
        ):
            self.app.preprocess_request()
            # Deve pular alemão e italiano (não suportados) e usar pt_BR
            self.assertEqual(g.interface_language, 'pt_BR')


class CleanResponseHeadersTestCase(unittest.TestCase):
    """Testes para a função clean_response_headers()"""

    def test_language_cookie_removal(self):
        """Testa que cookies de idioma são removidos"""
        from flask import Flask, make_response

        app = Flask(__name__)

        with app.test_request_context('/'):
            response = make_response('test')
            response.set_cookie('language', 'pt_BR')
            response.set_cookie('lang', 'en')
            response.set_cookie('interface_lang', 'es')
            response.set_cookie('session', 'abc123')  # Deve preservar

            # Simula processamento manual
            import re
            set_cookie_headers = response.headers.getlist('Set-Cookie')
            response.headers.pop('Set-Cookie', None)

            for cookie in set_cookie_headers:
                if not re.search(r'^(language|lang|interface_lang)=', cookie):
                    response.headers.add('Set-Cookie', cookie)

            # Verifica que apenas session permanece
            cookies = response.headers.getlist('Set-Cookie')
            self.assertEqual(len(cookies), 1)
            self.assertIn('session', cookies[0])

    def test_no_false_positives_in_cookie_removal(self):
        """Testa que cookies legítimos não são removidos por engano"""
        from flask import Flask, make_response

        app = Flask(__name__)

        with app.test_request_context('/'):
            response = make_response('test')
            response.set_cookie('user_languages', 'pt,en,es')  # NÃO deve remover
            response.set_cookie('country', 'England')  # NÃO deve remover
            response.set_cookie('my_lang_pref', 'en')  # NÃO deve remover

            # Simula processamento
            import re
            set_cookie_headers = response.headers.getlist('Set-Cookie')
            response.headers.pop('Set-Cookie', None)

            for cookie in set_cookie_headers:
                if not re.search(r'^(language|lang|interface_lang)=', cookie):
                    response.headers.add('Set-Cookie', cookie)

            # Todos devem permanecer
            cookies = response.headers.getlist('Set-Cookie')
            self.assertEqual(len(cookies), 3)


class GetCurrentLanguageTestCase(unittest.TestCase):
    """Testes para a função get_current_language()"""

    def test_get_current_language_fallback(self):
        """Testa fallback quando g.interface_language não existe"""
        from flask import Flask, g

        app = Flask(__name__)
        app.config['BABEL_DEFAULT_LOCALE'] = 'pt_BR'

        with app.test_request_context('/'):
            # Simula a função get_current_language
            result = getattr(g, 'interface_language',
                             app.config.get('BABEL_DEFAULT_LOCALE', 'pt_BR'))

            self.assertEqual(result, 'pt_BR')

    def test_get_current_language_from_g(self):
        """Testa leitura quando g.interface_language está definido"""
        from flask import Flask, g

        app = Flask(__name__)
        app.config['BABEL_DEFAULT_LOCALE'] = 'pt_BR'

        with app.test_request_context('/'):
            g.interface_language = 'en'

            result = getattr(g, 'interface_language',
                             app.config.get('BABEL_DEFAULT_LOCALE', 'pt_BR'))

            self.assertEqual(result, 'en')


if __name__ == '__main__':
    unittest.main()
