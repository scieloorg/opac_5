# coding: utf-8
"""
Filtros customizados para templates Jinja2.
"""


def make_absolute_url(url, base_url=''):
    """
    Retorna URL absoluta.

    Se a URL já for absoluta (começando com http:// ou https://),
    retorna como está. Caso contrário, concatena com base_url
    removendo barras duplicadas.

    Args:
        url (str): URL que pode ser relativa ou absoluta, ou None
        base_url (str): URL base para concatenação (ex: request.url_root)

    Returns:
        str: URL absoluta ou string vazia se url for None/vazio

    Exemplos:
        >>> make_absolute_url('https://cdn.example.com/logo.png', 'http://scielo.do')
        'https://cdn.example.com/logo.png'

        >>> make_absolute_url('/media/logo.png', 'http://scielo.do')
        'http://scielo.do/media/logo.png'

        >>> make_absolute_url('media/logo.png', 'http://scielo.do/')
        'http://scielo.do/media/logo.png'

        >>> make_absolute_url(None, 'http://scielo.do')
        ''
    """
    if not url:
        return ''

    # Se já é uma URL absoluta, retorna sem modificação
    if url.startswith(('http://', 'https://')):
        return url

    # Remove barra inicial da URL relativa
    url = url.lstrip('/')

    # Garante que base_url não termine com barra
    base_url = base_url.rstrip('/') if base_url else ''

    # Concatena apenas se houver base_url
    return f"{base_url}/{url}" if base_url else url
