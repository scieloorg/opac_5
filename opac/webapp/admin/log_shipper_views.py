# coding: utf-8
import flask_login as login
from flask_admin.contrib import sqla
from flask_babel import lazy_gettext as __

from log_shipper.links import minio_link_html


class LogShipmentAdminView(sqla.ModelView):
    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True
    page_size = 50
    column_default_sort = ("updated_at", True)
    column_filters = ["status"]
    column_searchable_list = ["relative_path", "object_key"]
    column_list = (
        "relative_path",
        "object_key",
        "status",
        "attempts",
        "last_error",
        "updated_at",
        "uploaded_at",
    )
    column_labels = dict(
        relative_path=__("Caminho"),
        object_key=__("MinIO"),
        status=__("Situação"),
        attempts=__("Tentativas"),
        last_error=__("Erro"),
        updated_at=__("Atualizado em"),
        uploaded_at=__("Enviado em"),
    )

    def _minio_formatter(self, context, model, name):
        return minio_link_html(model.status, model.object_key)

    column_formatters = {"object_key": _minio_formatter}

    def is_accessible(self):
        return login.current_user.is_authenticated


class LogShipperRunAdminView(sqla.ModelView):
    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True
    page_size = 50
    column_default_sort = ("started_at", True)
    column_filters = ["status"]
    column_list = (
        "started_at",
        "finished_at",
        "status",
        "pending_count",
        "uploaded_count",
        "failed_count",
        "error_message",
    )
    column_labels = dict(
        started_at=__("Início"),
        finished_at=__("Fim"),
        status=__("Situação"),
        pending_count=__("Pendentes"),
        uploaded_count=__("Enviados"),
        failed_count=__("Falhas"),
        error_message=__("Erro"),
    )

    def is_accessible(self):
        return login.current_user.is_authenticated
