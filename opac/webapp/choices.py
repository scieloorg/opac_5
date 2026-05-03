# coding: utf-8

from flask_babelex import gettext as _
from flask_babelex import lazy_gettext as __

UNPUBLISH_REASONS = [
    _("Conteúdo temporariamente indisponível"),
]

LANGUAGES_CHOICES = [
    ("pt_BR", __("Português")),
    ("en", __("Inglês")),
    ("es", __("Espanhol")),
]

INDEX_NAME = {
    "SCIE": "Science Citation Index",
    "SSCI": "Social Science Citation",
    "A&HCI": "Arts & Humanities Citation",
}

# Dicionário expandido de traduções de idiomas
# Estrutura: {codigo_iso: {idioma_interface: nome_traduzido}}
# Usado para traduzir nomes de idiomas nos menus de artigos (resumo, texto, PDF)
LANGUAGE_TRANSLATIONS = {
    'pt': {
        'pt': __('Português'),
        'en': __('Portuguese'),
        'es': __('Portugués')
    },
    'en': {
        'pt': __('Inglês'),
        'en': __('English'),
        'es': __('Inglés')
    },
    'es': {
        'pt': __('Espanhol'),
        'en': __('Spanish'),
        'es': __('Español')
    },
    'de': {
        'pt': __('Alemão'),
        'en': __('German'),
        'es': __('Alemán')
    },
    'fr': {
        'pt': __('Francês'),
        'en': __('French'),
        'es': __('Francés')
    },
    'it': {
        'pt': __('Italiano'),
        'en': __('Italian'),
        'es': __('Italiano')
    },
    'ru': {
        'pt': __('Russo'),
        'en': __('Russian'),
        'es': __('Ruso')
    },
    'ja': {
        'pt': __('Japonês'),
        'en': __('Japanese'),
        'es': __('Japonés')
    },
    'zh': {
        'pt': __('Chinês'),
        'en': __('Chinese'),
        'es': __('Chino')
    },
    'cn': {  # Alias para zh (compatibilidade com ISO3166_ALPHA2 existente)
        'pt': __('Chinês'),
        'en': __('Chinese'),
        'es': __('Chino')
    },
    'ar': {
        'pt': __('Árabe'),
        'en': __('Arabic'),
        'es': __('Árabe')
    },
    'ko': {
        'pt': __('Coreano'),
        'en': __('Korean'),
        'es': __('Coreano')
    },
    'nl': {
        'pt': __('Holandês'),
        'en': __('Dutch'),
        'es': __('Holandés')
    },
    'pl': {
        'pt': __('Polonês'),
        'en': __('Polish'),
        'es': __('Polaco')
    },
    'tr': {
        'pt': __('Turco'),
        'en': __('Turkish'),
        'es': __('Turco')
    },
    'sv': {
        'pt': __('Sueco'),
        'en': __('Swedish'),
        'es': __('Sueco')
    },
    'da': {
        'pt': __('Dinamarquês'),
        'en': __('Danish'),
        'es': __('Danés')
    },
    'no': {
        'pt': __('Norueguês'),
        'en': __('Norwegian'),
        'es': __('Noruego')
    },
    'fi': {
        'pt': __('Finlandês'),
        'en': __('Finnish'),
        'es': __('Finlandés')
    },
    'cs': {
        'pt': __('Tcheco'),
        'en': __('Czech'),
        'es': __('Checo')
    },
    'el': {
        'pt': __('Grego'),
        'en': __('Greek'),
        'es': __('Griego')
    },
    'he': {
        'pt': __('Hebraico'),
        'en': __('Hebrew'),
        'es': __('Hebreo')
    },
    'hi': {
        'pt': __('Hindi'),
        'en': __('Hindi'),
        'es': __('Hindi')
    },
    'th': {
        'pt': __('Tailandês'),
        'en': __('Thai'),
        'es': __('Tailandés')
    },
    'vi': {
        'pt': __('Vietnamita'),
        'en': __('Vietnamese'),
        'es': __('Vietnamita')
    },
    'id': {
        'pt': __('Indonésio'),
        'en': __('Indonesian'),
        'es': __('Indonesio')
    },
    'ms': {
        'pt': __('Malaio'),
        'en': __('Malay'),
        'es': __('Malayo')
    },
    'ca': {
        'pt': __('Catalão'),
        'en': __('Catalan'),
        'es': __('Catalán')
    },
    'gl': {
        'pt': __('Galego'),
        'en': __('Galician'),
        'es': __('Gallego')
    },
    'eu': {
        'pt': __('Basco'),
        'en': __('Basque'),
        'es': __('Vasco')
    },
    'ro': {
        'pt': __('Romeno'),
        'en': __('Romanian'),
        'es': __('Rumano')
    },
    'hu': {
        'pt': __('Húngaro'),
        'en': __('Hungarian'),
        'es': __('Húngaro')
    },
    'uk': {
        'pt': __('Ucraniano'),
        'en': __('Ukrainian'),
        'es': __('Ucraniano')
    },
    'hr': {
        'pt': __('Croata'),
        'en': __('Croatian'),
        'es': __('Croata')
    },
    'sr': {
        'pt': __('Sérvio'),
        'en': __('Serbian'),
        'es': __('Serbio')
    },
    'bg': {
        'pt': __('Búlgaro'),
        'en': __('Bulgarian'),
        'es': __('Búlgaro')
    },
    'sk': {
        'pt': __('Eslovaco'),
        'en': __('Slovak'),
        'es': __('Eslovaco')
    },
    'sl': {
        'pt': __('Esloveno'),
        'en': __('Slovenian'),
        'es': __('Esloveno')
    },
    'lt': {
        'pt': __('Lituano'),
        'en': __('Lithuanian'),
        'es': __('Lituano')
    },
    'lv': {
        'pt': __('Letão'),
        'en': __('Latvian'),
        'es': __('Letón')
    },
    'et': {
        'pt': __('Estoniano'),
        'en': __('Estonian'),
        'es': __('Estonio')
    },
    'al': {  # Alias (compatibilidade com ISO3166_ALPHA2 existente)
        'pt': __('Albanês'),
        'en': __('Albanian'),
        'es': __('Albanés')
    },
    'sq': {  # Código ISO correto para albanês
        'pt': __('Albanês'),
        'en': __('Albanian'),
        'es': __('Albanés')
    }
}

# Mantido por compatibilidade - usar LANGUAGE_TRANSLATIONS para novos códigos
ISO3166_ALPHA2 = {
    "pt": __("Português"),
    "en": __("Inglês"),
    "es": __("Espanhol"),
    "al": __("Albanês"),
    "cn": __("Chinês"),
    "ro": __("Romeno"),
    "fr": __("Francês"),
    "it": __("Italiano"),
    "ru": __("Russo"),
    "ar": __("Árabe"),
    "zh": __("Chinês"),
}

JOURNAL_STATUS = {
    "current": __("corrente"),
    "deceased": __("terminado"),
    "suspended": __("indexação interrompida"),
    "interrupted": __("indexação interrompida pelo Comitê"),
    "finished": __("publicação finalizada"),
}

STUDY_AREAS = {
    "AGRICULTURAL SCIENCES": __("Ciências Agrárias"),
    "APPLIED SOCIAL SCIENCES": __("Ciências Sociais Aplicadas"),
    "BIOLOGICAL SCIENCES": __("Ciências Biológicas"),
    "ENGINEERING": __("Engenharias"),
    "EXACT AND EARTH SCIENCES": __("Ciências Exatas e da Terra"),
    "HEALTH SCIENCES": __("Ciências da Saúde"),
    "HUMAN SCIENCES": __("Ciências Humanas"),
    "LINGUISTICS, LETTERS AND ARTS": __("Lingüística, Letras e Artes"),
    "LINGUISTICS, LITERATURE AND ARTS": __("Lingüística, Letras e Artes"),
}
