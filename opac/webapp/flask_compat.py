# coding: utf-8

import logging

logger = logging.getLogger(__name__)

_PATCHED = False


def apply_flask_23_compat():
    """Apply compatibility shims for third-party packages on Flask 2.3–3.x."""
    global _PATCHED

    if _PATCHED:
        return

    _patch_json_encoder()
    _patch_flask_mongoengine_json()
    _patch_before_app_first_request()
    _PATCHED = True
    logger.debug("Applied Flask 2.3 compatibility patches.")


def _patch_json_encoder():
    """Restore flask.json.JSONEncoder for flask-mongoengine."""
    import json

    import flask.json as flask_json

    if hasattr(flask_json, "JSONEncoder"):
        return

    class JSONEncoder(json.JSONEncoder):
        pass

    flask_json.JSONEncoder = JSONEncoder


def _patch_flask_mongoengine_json():
    """Fix flask-mongoengine JSONEncoder setup on Flask 2.3+."""
    import json

    import flask_mongoengine
    import flask_mongoengine.json as me_json

    def override_json_encoder(app):
        app.json_encoder = me_json._make_encoder(json.JSONEncoder)

    me_json.override_json_encoder = override_json_encoder
    flask_mongoengine.override_json_encoder = override_json_encoder


def _patch_before_app_first_request():
    """Patch Blueprint.before_app_first_request for rq-dashboard packages."""
    from functools import wraps

    from flask import Blueprint

    if hasattr(Blueprint, "before_app_first_request"):
        return

    def before_app_first_request(self, f):
        @wraps(f)
        def wrapper(state):
            return f()

        self.record_once(wrapper)
        return f

    Blueprint.before_app_first_request = before_app_first_request
