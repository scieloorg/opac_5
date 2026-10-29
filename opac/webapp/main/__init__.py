# coding: utf-8
from flask import Blueprint

main = Blueprint("main", __name__)
restapi = Blueprint("restapi", __name__, url_prefix="/api/v1")
restapi_v2 = Blueprint("restapi_v2", __name__, url_prefix="/api/v2")

from . import errors, views  # NOQA
