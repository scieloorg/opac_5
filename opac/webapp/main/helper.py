import datetime
from functools import wraps
from urllib.parse import urlencode

import jwt
from flask import jsonify, request, session
from flask_babelex import get_locale
from webapp import controllers
from werkzeug.security import check_password_hash
from flask import current_app


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get("token")
        if not token:
            return jsonify({"message": "token is missing", "data": []}), 401
        try:
            data = jwt.decode(
                token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
            )
            current_user = controllers.get_user_by_email(email=data["email"])
        except:
            return jsonify({"message": "token is invalid or expired", "data": []}), 401
        return f(current_user, *args, **kwargs)

    return decorated


# Gerando token com base na Secret key do app e definindo expiração com 'exp'
def auth():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return (
            jsonify(
                {
                    "message": "could not verify",
                    "WWW-Authenticate": 'Basic auth="Login required"',
                }
            ),
            401,
        )
    user = controllers.get_user_by_email(auth.username)
    if not user:
        return jsonify({"message": "user not found", "data": []}), 401

    if user and check_password_hash(user.password, auth.password):
        token = jwt.encode(
            {
                "email": user.email,
                "exp": datetime.datetime.now() + datetime.timedelta(hours=12),
            },
            current_app.config["SECRET_KEY"],
        )
        return jsonify(
            {
                "message": "Validated successfully",
                "token": token,
                "exp": datetime.datetime.now() + datetime.timedelta(hours=12),
            }
        )

    return (
        jsonify(
            {
                "message": "could not verify",
                "WWW-Authenticate": 'Basic auth="Login required"',
            }
        ),
        401,
    )


def build_classic_website_uri(resource_type, resource=None, **kwargs):
    """
    Constrói a URI completa para o site clássico com base no tipo de recurso.
    
    Args:
        resource_type: tipo do recurso ('journal', 'issue', 'article')
        resource: objeto do recurso (Journal, Issue, ou Article)
        **kwargs: parâmetros adicionais (ex: lang)
    
    Returns:
        String com a URI completa para o site clássico ou None se não puder ser construída
    """
    classic_site_url = current_app.config.get("PREVIOUS_WEBSITE_URI", "")
    if not classic_site_url:
        return None
    
    # Obter idioma da sessão ou usar o padrão
    lang = kwargs.get('lang') or session.get("lang", str(get_locale()))
    if lang and len(lang) > 2:
        lang = lang[:2]  # Converter pt_BR para pt
    
    base_url = classic_site_url.rstrip("/")
    
    try:
        if resource_type == 'journal' and resource:
            # Usa print_issn ou electronic_issn
            issn = getattr(resource, 'print_issn', None) or getattr(resource, 'electronic_issn', None)
            if issn:
                params = {'script': 'sci_serial', 'pid': issn, 'lng': lang, 'nrm': 'iso'}
                return f"{base_url}/scielo.php?{urlencode(params)}"
        
        elif resource_type == 'issue' and resource:
            # Usa o PID do issue
            pid = getattr(resource, 'pid', None)
            if pid:
                params = {'script': 'sci_issuetoc', 'pid': pid, 'lng': lang, 'nrm': 'iso'}
                return f"{base_url}/scielo.php?{urlencode(params)}"
        
        elif resource_type == 'article' and resource:
            # Usa o PID v2 do artigo
            pid = getattr(resource, 'pid', None)
            if pid:
                params = {'script': 'sci_arttext', 'pid': pid, 'lng': lang, 'nrm': 'iso'}
                return f"{base_url}/scielo.php?{urlencode(params)}"
    
    except Exception:
        # Se houver qualquer erro ao construir a URL, retorna None
        pass
    
    return None
