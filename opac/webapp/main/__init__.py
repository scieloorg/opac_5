# coding: utf-8
from flask import Blueprint

main = Blueprint("main", __name__)
restapi = Blueprint("restapi", __name__, url_prefix="/api/v1")

from . import errors, views  # NOQA
