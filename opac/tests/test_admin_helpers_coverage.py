# coding: utf-8

import os
import tempfile
from unittest.mock import Mock, patch

from flask import current_app
from PIL import Image
from werkzeug.datastructures import MultiDict
from wtforms import Form
from webapp.admin import forms
from webapp.admin.ajax import CustomQueryAjaxModelLoader
from webapp.admin.custom_fields import (
    MediaFileUploadField,
    MediaImageUploadField,
    RequiredBooleanField,
)
from webapp.admin.custom_widget import CKEditorField, CKEditorWidget
from tests.utils import makeOneJournal

from .base import BaseTestCase


class AdminHelpersCoverageTestCase(BaseTestCase):
    def test_required_boolean_field_init_and_coerce(self):
        class _BooleanForm(Form):
            enabled = RequiredBooleanField("enabled")

        form = _BooleanForm()
        self.assertEqual(
            [(True, "True"), (False, "False")],
            form.enabled.choices,
        )
        self.assertTrue(form.enabled.coerce("True"))
        self.assertFalse(form.enabled.coerce("False"))

    def test_media_image_upload_field_defaults(self):
        class _ImageForm(Form):
            image = MediaImageUploadField()

        with current_app.app_context():
            form = _ImageForm()
            field = form.image
            self.assertEqual("File", field.label.text)
            self.assertEqual(current_app.config["MEDIA_ROOT"], field.base_path)
            self.assertEqual("images/", field.relative_path)
            self.assertEqual(
                current_app.config["IMAGES_ALLOWED_EXTENSIONS"],
                field.allowed_extensions,
            )
            self.assertEqual("main.download_file_by_filename", field.endpoint)

    def test_media_image_upload_field_custom_endpoint(self):
        class _ImageForm(Form):
            image = MediaImageUploadField(
                label="Logo",
                base_path="/tmp/media",
                relative_path="custom/",
                endpoint="static",
            )

        with current_app.app_context():
            form = _ImageForm()
            field = form.image
            self.assertEqual("Logo", field.label.text)
            self.assertEqual("/tmp/media", field.base_path)
            self.assertEqual("custom/", field.relative_path)
            self.assertEqual("static", field.endpoint)

    def test_media_image_upload_field_custom_namegen_and_extensions(self):
        class _ImageForm(Form):
            image = MediaImageUploadField(
                namegen=lambda obj, file_data: "custom-image-name",
                allowed_extensions=("png",),
            )

        with current_app.app_context():
            field = _ImageForm().image
            self.assertEqual(("png",), field.allowed_extensions)

    def test_media_image_upload_field_save_image_keeps_rgb_mode(self):
        class _ImageForm(Form):
            image = MediaImageUploadField()

        with current_app.app_context():
            field = _ImageForm().image
            image = Image.new("RGB", (10, 10), color="red")
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                path = tmp.name
            try:
                field._save_image(image, path)
                saved = Image.open(path)
                self.assertEqual("RGB", saved.mode)
            finally:
                os.unlink(path)

    def test_media_image_upload_field_save_image_converts_palette_mode(self):
        class _ImageForm(Form):
            image = MediaImageUploadField()

        with current_app.app_context():
            field = _ImageForm().image
            image = Image.new("P", (10, 10))
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                path = tmp.name
            try:
                field._save_image(image, path)
                saved = Image.open(path)
                self.assertEqual("RGB", saved.mode)
            finally:
                os.unlink(path)

    def test_media_file_upload_field_defaults(self):
        class _FileForm(Form):
            attachment = MediaFileUploadField()

        with current_app.app_context():
            field = _FileForm().attachment
            self.assertEqual("File", field.label.text)
            self.assertEqual(current_app.config["MEDIA_ROOT"], field.base_path)
            self.assertEqual("files/", field.relative_path)
            self.assertEqual(
                current_app.config["FILES_ALLOWED_EXTENSIONS"],
                field.allowed_extensions,
            )

    def test_media_file_upload_field_custom_values(self):
        with current_app.app_context():

            def custom_namegen(obj, file_data):
                return "custom-name"

            class _FileForm(Form):
                attachment = MediaFileUploadField(
                    label="Attachment",
                    base_path="/tmp/files",
                    relative_path="docs/",
                    namegen=custom_namegen,
                    allowed_extensions=("pdf",),
                )

            field = _FileForm().attachment
            self.assertEqual("Attachment", field.label.text)
            self.assertEqual("/tmp/files", field.base_path)
            self.assertEqual("docs/", field.relative_path)
            self.assertEqual(("pdf",), field.allowed_extensions)

    def test_ckeditor_widget_render_with_and_without_class(self):
        class _TestForm(Form):
            content = CKEditorField()

        form = _TestForm()
        widget = CKEditorWidget()
        html_default = widget(form.content)
        self.assertIn('class="ckeditor"', html_default)

        html_with_class = widget(form.content, **{"class": "foo"})
        self.assertIn('class="foo ckeditor"', html_with_class)

    def test_email_form_validate_and_invalidate(self):
        valid_form = forms.EmailForm(
            formdata=MultiDict([("email", "user@example.com")])
        )
        self.assertTrue(valid_form.validate())

        invalid_form = forms.EmailForm(formdata=MultiDict([("email", "not-an-email")]))
        self.assertFalse(invalid_form.validate())
        self.assertIn("email", invalid_form.errors)

    def test_login_form_validate_password_invalid_user_and_password(self):
        with patch("webapp.admin.forms.controllers.get_user_by_email", return_value=None):
            form = forms.LoginForm(
                formdata=MultiDict(
                    [("email", "missing@example.com"), ("password", "x")]
                )
            )
            self.assertFalse(form.validate())
            self.assertIn("password", form.errors)

        user = Mock()
        user.is_correct_password.return_value = False
        with patch("webapp.admin.forms.controllers.get_user_by_email", return_value=user):
            form = forms.LoginForm(
                formdata=MultiDict(
                    [("email", "user@example.com"), ("password", "wrong")]
                )
            )
            self.assertFalse(form.validate())
            self.assertIn("password", form.errors)

        user.is_correct_password.return_value = True
        with patch("webapp.admin.forms.controllers.get_user_by_email", return_value=user):
            form = forms.LoginForm(
                formdata=MultiDict(
                    [("email", "user@example.com"), ("password", "secret")]
                )
            )
            self.assertTrue(form.validate())

    def test_custom_query_ajax_model_loader_format_and_get_one(self):
        journal = makeOneJournal({"title": "ajax-coverage-journal"})
        loader = CustomQueryAjaxModelLoader(
            name="journal",
            model=type(journal),
            fields=["title", "acronym"],
        )

        self.assertIsNone(loader.format(None))
        formatted = loader.format(journal)
        self.assertEqual(str(journal._id), formatted[0])
        self.assertEqual(str(journal), formatted[1])

        loaded = loader.get_one(journal._id)
        self.assertEqual(journal._id, loaded._id)
