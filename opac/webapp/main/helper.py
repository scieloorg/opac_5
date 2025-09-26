import datetime
from functools import wraps

import jwt
from flask import jsonify, request
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


def get_bearer_token():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):]
    return None

def verify_jwt(token):
    return jwt.decode(
        token,
        current_app.config["JWT_PUBLIC_KEY_PEM"],
        algorithms=[current_app.config["JWT_ALG"]],
        audience=current_app.config["JWT_AUD"],
        issuer=current_app.config["JWT_ISS"],
        # options={"require": ["exp", "iat", "nbf", "iss", "aud"]},
        leeway=30,
    )