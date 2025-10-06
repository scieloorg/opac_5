import logging
from functools import wraps

from flask import g, jsonify
from jwt import PyJWTError

from .helper import get_bearer_token, verify_jwt


def require_jwt(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = get_bearer_token()
        if not token:
            return jsonify({"detail": "Missing Bearer token"}), 401
        try:
            g.jwt = verify_jwt(token)            
        except PyJWTError as e:
            logging.error("Erro na validação JWT:", str(e))
            return jsonify({"detail": f"Invalid token: {str(e)}"}), 401
        return f(*args, **kwargs)
    return wrapper