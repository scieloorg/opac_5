# coding: utf-8

import importlib
import os
import sys
import tempfile
from contextlib import contextmanager
from unittest.mock import MagicMock, Mock, patch

from flask import Flask, current_app
from wtforms.validators import ValidationError

from webapp import configure_apm_agent, create_app, dbsql
from webapp import flask_compat, wtforms_compat
from webapp.exceptions import LinkDocumentToDocumentsBundleException
from webapp.forms import EmailShareForm
from webapp.models import File, Image, User

from .base import BaseTestCase


class ConfigureApmAgentTestCase(BaseTestCase):
    def _apm_app(self, **config):
        app = Flask(__name__)
        app.config.update({"APM_ENABLED": False, **config})
        return app

    def test_configure_apm_agent_disabled(self):
        app = self._apm_app(APM_ENABLED=False)
        self.assertIsNone(configure_apm_agent(app))

    def test_configure_apm_agent_missing_required_server_url(self):
        app = self._apm_app(APM_ENABLED=True)
        with self.assertRaises(ValueError) as ctx:
            configure_apm_agent(app)
        self.assertIn("APM_SERVER_URL", str(ctx.exception))

    def test_configure_apm_agent_empty_required_server_url(self):
        app = self._apm_app(APM_ENABLED=True, APM_SERVER_URL="")
        with self.assertRaises(ValueError) as ctx:
            configure_apm_agent(app)
        self.assertIn("APM_SERVER_URL", str(ctx.exception))

    def test_configure_apm_agent_invalid_cast(self):
        app = self._apm_app(
            APM_ENABLED=True,
            APM_SERVER_URL="http://apm.example",
            APM_LOCAL_VAR_MAX_LENGTH="not-an-int",
        )
        with self.assertRaises(ValueError) as ctx:
            configure_apm_agent(app)
        self.assertIn("APM_LOCAL_VAR_MAX_LENGTH", str(ctx.exception))

    @patch("webapp.ElasticAPM")
    def test_configure_apm_agent_success(self, mock_elastic_apm):
        mock_elastic_apm.return_value = Mock(name="apm_client")
        app = self._apm_app(
            APM_ENABLED=True,
            APM_SERVER_URL="http://apm.example",
            APM_SERVICE_NAME="opac-test",
            APM_CAPTURE_HEADERS="true",
            APM_DEBUG="false",
        )
        result = configure_apm_agent(app)
        self.assertIs(result, mock_elastic_apm.return_value)
        self.assertEqual("http://apm.example", app.config["ELASTIC_APM"]["SERVER_URL"])
        self.assertTrue(app.config["ELASTIC_APM"]["CAPTURE_HEADERS"])
        mock_elastic_apm.assert_called_once_with(app)


class CreateAppBranchesTestCase(BaseTestCase):
    def _write_config(self, **overrides):
        lines = ["APM_ENABLED = False"]
        for key, value in overrides.items():
            if isinstance(value, bool):
                rendered = "True" if value else "False"
            elif isinstance(value, str):
                rendered = repr(value)
            else:
                rendered = repr(value)
            lines.append("%s = %s" % (key, rendered))
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        )
        handle.write("\n".join(lines))
        handle.close()
        return handle.name

    def _create_app_with_config(self, config_path, **patches):
        patchers = []
        for target, mock_obj in patches.items():
            patchers.append(patch(target, mock_obj))
        for patcher in patchers:
            patcher.start()
        try:
            with patch.dict(os.environ, {"OPAC_CONFIG": config_path}, clear=False):
                return create_app()
        finally:
            for patcher in reversed(patchers):
                patcher.stop()
            os.unlink(config_path)

    @patch("webapp.Sentry.init_app")
    def test_create_app_initializes_sentry_when_enabled(self, mock_sentry_init):
        config_path = self._write_config(
            USE_SENTRY=True, SENTRY_DSN="https://example@sentry.io/1"
        )
        self._create_app_with_config(config_path)
        mock_sentry_init.assert_called_once()

    @patch("webapp.HTMLMIN")
    def test_create_app_enables_html_minification(self, mock_htmlmin):
        config_path = self._write_config(MINIFY_PAGE=True)
        self._create_app_with_config(config_path)
        mock_htmlmin.assert_called_once()

    def test_create_app_enables_debug_toolbar(self):
        fake_toolbar = MagicMock()
        fake_module = MagicMock(DebugToolbarExtension=fake_toolbar)
        config_path = self._write_config(DEBUG=True)
        with patch.dict(sys.modules, {"flask_debugtoolbar": fake_module}):
            self._create_app_with_config(config_path)
        fake_toolbar.assert_called_once()
        fake_toolbar.return_value.init_app.assert_called_once()

    @patch("webapp.cache.init_app")
    def test_create_app_cache_enabled_branch(self, mock_cache_init):
        config_path = self._write_config(CACHE_ENABLED=True)
        app = self._create_app_with_config(config_path)
        mock_cache_init.assert_called_once_with(app, config=app.config)

    @patch("webapp.cache.init_app")
    def test_create_app_cache_disabled_branch(self, mock_cache_init):
        config_path = self._write_config(CACHE_ENABLED=False)
        app = self._create_app_with_config(config_path)
        self.assertEqual("null", app.config["CACHE_TYPE"])
        mock_cache_init.assert_called_once_with(app, config=app.config)

    def test_check_user_logged_in_or_redirect_for_scheduler(self):
        handlers = current_app.before_request_funcs.get(None, [])
        redirect_handler = handlers[-1]

        with current_app.test_request_context("/admin/scheduler"):
            with patch("webapp.current_user") as mock_user:
                mock_user.is_authenticated = False
                response = redirect_handler()

        self.assertIsNotNone(response)
        self.assertEqual(302, response.status_code)
        self.assertIn("login", response.location)

    def test_check_user_logged_in_or_redirect_for_workers(self):
        handlers = current_app.before_request_funcs.get(None, [])
        redirect_handler = handlers[-1]

        with current_app.test_request_context("/admin/workers"):
            with patch("webapp.current_user") as mock_user:
                mock_user.is_authenticated = False
                response = redirect_handler()

        self.assertIsNotNone(response)
        self.assertEqual(302, response.status_code)
        self.assertIn("login", response.location)

    def test_check_user_logged_in_or_redirect_skips_authenticated_user(self):
        handlers = current_app.before_request_funcs.get(None, [])
        redirect_handler = handlers[-1]

        with current_app.test_request_context("/admin/scheduler"):
            with patch("webapp.current_user") as mock_user:
                mock_user.is_authenticated = True
                self.assertIsNone(redirect_handler())


class RegexConverterTestCase(BaseTestCase):
    def test_regex_converter_sets_pattern(self):
        from webapp import RegexConverter

        app = Flask(__name__)
        converter = RegexConverter(app.url_map, r"\d+")
        self.assertEqual(r"\d+", converter.regex)


class FlaskCompatTestCase(BaseTestCase):
    def tearDown(self):
        flask_compat._PATCHED = False
        super(FlaskCompatTestCase, self).tearDown()

    def test_apply_flask_23_compat_early_return_when_already_patched(self):
        flask_compat._PATCHED = True
        with patch.object(flask_compat, "_patch_before_app_first_request") as mock_patch:
            flask_compat.apply_flask_23_compat()
        mock_patch.assert_not_called()

    def test_patch_before_app_first_request_skips_when_attribute_exists(self):
        from flask import Blueprint

        original = getattr(Blueprint, "before_app_first_request", None)
        sentinel = lambda self, f: f
        Blueprint.before_app_first_request = sentinel
        try:
            flask_compat._patch_before_app_first_request()
            self.assertIs(sentinel, Blueprint.before_app_first_request)
        finally:
            if original is None:
                delattr(Blueprint, "before_app_first_request")
            else:
                Blueprint.before_app_first_request = original

    def test_patch_before_app_first_request_adds_shim(self):
        from flask import Blueprint

        flask_compat._PATCHED = False
        original = getattr(Blueprint, "before_app_first_request", None)
        try:
            if hasattr(Blueprint, "before_app_first_request"):
                delattr(Blueprint, "before_app_first_request")
            flask_compat._patch_before_app_first_request()
            self.assertTrue(hasattr(Blueprint, "before_app_first_request"))
            bp = Blueprint("test_bp", __name__)

            @bp.before_app_first_request
            def on_first_request():
                return "ok"

            recorded = []
            bp.record_once = lambda func: recorded.append(func)
            bp.before_app_first_request(on_first_request)
            self.assertEqual(1, len(recorded))
        finally:
            flask_compat._PATCHED = False
            if original is None:
                if hasattr(Blueprint, "before_app_first_request"):
                    delattr(Blueprint, "before_app_first_request")
            else:
                Blueprint.before_app_first_request = original


class WTFormsCompatTestCase(BaseTestCase):
    def tearDown(self):
        wtforms_compat._PATCHED = False
        super(WTFormsCompatTestCase, self).tearDown()

    @patch("webapp.wtforms_compat._wtforms_major_minor", return_value=(3, 2))
    def test_iter_choice_for_wtforms_32_plus(self, _mock_version):
        self.assertEqual((1, "One", True, {}), wtforms_compat.iter_choice(1, "One", True))

    @patch("webapp.wtforms_compat._wtforms_major_minor", return_value=(3, 1))
    def test_iter_choice_for_wtforms_before_32(self, _mock_version):
        self.assertEqual((1, "One", True), wtforms_compat.iter_choice(1, "One", True))

    @patch("webapp.wtforms_compat._wtforms_major_minor", return_value=(3, 2))
    def test_apply_wtforms_compat_early_return_when_patched(self, _mock_version):
        wtforms_compat._PATCHED = True
        with patch("webapp.wtforms_compat._patch_iter_choices_method") as mock_patch:
            wtforms_compat.apply_wtforms_compat()
        mock_patch.assert_not_called()

    @patch("webapp.wtforms_compat._wtforms_major_minor", return_value=(3, 1))
    def test_apply_wtforms_compat_early_return_for_old_wtforms(self, _mock_version):
        wtforms_compat._PATCHED = False
        with patch("webapp.wtforms_compat._patch_iter_choices_method") as mock_patch:
            wtforms_compat.apply_wtforms_compat()
        mock_patch.assert_not_called()

    @patch("webapp.wtforms_compat._wtforms_major_minor", return_value=(3, 2))
    def test_patch_iter_choices_yields_compat_and_passthrough_tuples(self, _mock_version):
        class DummyField(object):
            def iter_choices(self):
                yield (1, "One", True)
                yield ("raw",)

        wtforms_compat._patch_iter_choices_method(DummyField)
        field = DummyField()
        self.assertEqual([(1, "One", True, {}), ("raw",)], list(field.iter_choices()))

    @patch("webapp.wtforms_compat._wtforms_major_minor", return_value=(3, 2))
    def test_patch_iter_choices_skips_already_patched_method(self, _mock_version):
        class DummyField(object):
            def iter_choices(self):
                yield (1, "One", True)

        DummyField.iter_choices._wtforms_compat_patched = True
        original = DummyField.iter_choices
        wtforms_compat._patch_iter_choices_method(DummyField)
        self.assertIs(original, DummyField.iter_choices)

    @patch("webapp.wtforms_compat._wtforms_major_minor", return_value=(3, 2))
    def test_apply_wtforms_compat_patches_query_fields(self, _mock_version):
        wtforms_compat._PATCHED = False
        from flask_admin.contrib.sqla import fields as sqla_fields

        wtforms_compat.apply_wtforms_compat()
        self.assertTrue(wtforms_compat._PATCHED)
        self.assertTrue(
            getattr(
                sqla_fields.QuerySelectField.iter_choices,
                "_wtforms_compat_patched",
                False,
            )
        )


class ModelsGlueCoverageTestCase(BaseTestCase):
    def test_user_password_property_and_unicode(self):
        user = User(email="glue@example.com")
        user.define_password("secret")
        self.assertEqual(user._password, user.password)
        self.assertEqual("glue@example.com", user.__unicode__())

    def test_user_password_setter(self):
        user = User(email="glue@example.com")
        user.password = "via-setter"
        self.assertTrue(user.is_correct_password("via-setter"))

    def test_user_check_valid_email_with_empty_string(self):
        user = User(email="")
        self.assertFalse(user._check_valid_email())

    def test_user_check_valid_email_with_valid_email(self):
        user = User(email="glue@example.com")
        self.assertTrue(user._check_valid_email())

    def test_user_send_confirmation_email_invalid_email_raises(self):
        user = User(email="")
        with self.assertRaises(ValueError):
            user.send_confirmation_email()

    def test_user_send_reset_password_email_invalid_email_raises(self):
        user = User(email="")
        with self.assertRaises(ValueError):
            user.send_reset_password_email()

    def test_is_correct_password_without_hash_returns_false(self):
        user = User(email="glue@example.com")
        user._password = None
        self.assertFalse(user.is_correct_password("secret"))

    @patch("webapp.models.notifications.send_confirmation_email", return_value=(True, ""))
    def test_user_send_confirmation_email_delegates_to_notifications(self, mock_send):
        user = User(email="glue@example.com")
        self.assertEqual((True, ""), user.send_confirmation_email())
        mock_send.assert_called_once_with("glue@example.com")

    @patch("webapp.models.notifications.send_reset_password_email", return_value=(True, ""))
    def test_user_send_reset_password_email_delegates_to_notifications(self, mock_send):
        user = User(email="glue@example.com")
        self.assertEqual((True, ""), user.send_reset_password_email())
        mock_send.assert_called_once_with("glue@example.com")

    def test_load_user_returns_user_by_id(self):
        from webapp.models import load_user

        user = User(email="load-user@example.com")
        dbsql.session.add(user)
        dbsql.session.commit()
        loaded = load_user(user.id)
        self.assertEqual(user.email, loaded.email)

    def test_file_unicode_and_absolute_url(self):
        record = File(name="doc.txt", path="files/doc.txt", language="en")
        self.assertEqual("doc.txt", record.__unicode__())
        expected = "%s/%s" % (
            self.app.config["MEDIA_URL"],
            "files/doc.txt",
        )
        self.assertEqual(expected, record.get_absolute_url)

    def test_image_unicode_and_urls(self):
        record = Image(name="pic.png", path="images/pic.png", language="pt")
        self.assertEqual("pic.png", record.__unicode__())
        self.assertIn("images/pic.png", record.get_absolute_url)
        self.assertIn("images/pic_thumb.png", record.get_thumbnail_absolute_url)

    def test_file_delete_hook_removes_file(self):
        media_root = tempfile.mkdtemp()
        rel_path = "glue/file.txt"
        abs_path = os.path.join(media_root, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w") as handle:
            handle.write("data")

        original_media_root = self.app.config["MEDIA_ROOT"]
        self.app.config["MEDIA_ROOT"] = media_root
        try:
            record = File(name="file.txt", path=rel_path)
            dbsql.session.add(record)
            dbsql.session.commit()
            dbsql.session.delete(record)
            dbsql.session.commit()
            self.assertFalse(os.path.exists(abs_path))
        finally:
            self.app.config["MEDIA_ROOT"] = original_media_root

    def test_file_delete_hook_ignores_os_error(self):
        record = File(name="missing.txt", path="missing.txt")
        with patch("webapp.models.os.remove", side_effect=OSError("missing")):
            from webapp.models import delelte_file_hook

            delelte_file_hook(None, None, record)

    def test_image_delete_hook_removes_image_and_thumbnail(self):
        media_root = tempfile.mkdtemp()
        rel_path = "glue/image.png"
        abs_path = os.path.join(media_root, rel_path)
        thumb_rel = "glue/image_thumb.png"
        thumb_abs = os.path.join(media_root, thumb_rel)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        for path in (abs_path, thumb_abs):
            with open(path, "w") as handle:
                handle.write("data")

        original_media_root = self.app.config["MEDIA_ROOT"]
        self.app.config["MEDIA_ROOT"] = media_root
        try:
            record = Image(name="image.png", path=rel_path)
            dbsql.session.add(record)
            dbsql.session.commit()
            dbsql.session.delete(record)
            dbsql.session.commit()
            self.assertFalse(os.path.exists(abs_path))
            self.assertFalse(os.path.exists(thumb_abs))
        finally:
            self.app.config["MEDIA_ROOT"] = original_media_root

    def test_image_delete_hook_skips_when_path_empty(self):
        record = Image(name="empty.png", path="")
        with patch("webapp.models.os.remove") as mock_remove:
            from webapp.models import delelte_image_hook

            delelte_image_hook(None, None, record)
        mock_remove.assert_not_called()


    def test_image_delete_hook_ignores_os_error(self):
        record = Image(name="missing.png", path="missing.png")
        with patch("webapp.models.os.remove", side_effect=OSError("missing")):
            from webapp.models import delelte_image_hook

            delelte_image_hook(None, None, record)

    def test_file_delete_hook_skips_when_path_empty(self):
        record = File(name="empty.txt", path="")
        with patch("webapp.models.os.remove") as mock_remove:
            from webapp.models import delelte_file_hook

            delelte_file_hook(None, None, record)
        mock_remove.assert_not_called()


class FormsGlueCoverageTestCase(BaseTestCase):
    @contextmanager
    def _without_csrf(self):
        previous = current_app.config.get("WTF_CSRF_ENABLED")
        current_app.config["WTF_CSRF_ENABLED"] = False
        try:
            yield
        finally:
            if previous is None:
                current_app.config.pop("WTF_CSRF_ENABLED", None)
            else:
                current_app.config["WTF_CSRF_ENABLED"] = previous

    def _valid_form_data(self, **overrides):
        data = {
            "your_email": "sender@example.com",
            "recipients": "one@example.com; two@example.com",
            "share_url": "https://example.com/article/1",
            "subject": "Check this out",
            "comment": "Hello",
        }
        data.update(overrides)
        return data

    def test_email_share_form_valid_recipients(self):
        with self.app.test_request_context():
            with self._without_csrf():
                form = EmailShareForm(data=self._valid_form_data())
                self.assertTrue(form.validate())

    def test_email_share_form_invalid_recipient_raises_validation_error(self):
        with self.app.test_request_context():
            with self._without_csrf():
                form = EmailShareForm(
                    data=self._valid_form_data(recipients="not-an-email")
                )
                self.assertFalse(form.validate())
                self.assertIn("recipients", form.errors)

    def test_email_share_form_ignores_empty_recipient_segments(self):
        with self.app.test_request_context():
            with self._without_csrf():
                form = EmailShareForm(
                    data=self._valid_form_data(recipients="one@example.com;; ")
                )
                self.assertTrue(form.validate())

    def test_email_share_form_validate_recipients_direct_invalid(self):
        form = EmailShareForm()
        field = Mock()
        field.data = "bad-email"
        with self.assertRaises(ValidationError):
            EmailShareForm.validate_recipients(form, field)


class ExceptionsGlueCoverageTestCase(BaseTestCase):
    def test_link_document_exception_without_response(self):
        exc = LinkDocumentToDocumentsBundleException("failed")
        self.assertEqual("failed", exc.message)
        self.assertFalse(hasattr(exc, "response"))

    def test_link_document_exception_with_response(self):
        response = Mock(status_code=500)
        exc = LinkDocumentToDocumentsBundleException("failed", response=response)
        self.assertEqual("failed", exc.message)
        self.assertIs(response, exc.response)


class DefaultConfigGlueCoverageTestCase(BaseTestCase):
    def test_mongodb_settings_include_credentials_when_env_set(self):
        from webapp.config import default as default_config

        env = {
            "OPAC_MONGODB_USER": "mongo-user",
            "OPAC_MONGODB_PASS": "mongo-pass",
        }
        original_settings = default_config.MONGODB_SETTINGS
        try:
            with patch.dict(os.environ, env, clear=False):
                importlib.reload(default_config)
            self.assertEqual(
                "mongo-user", default_config.MONGODB_SETTINGS[0]["username"]
            )
            self.assertEqual(
                "mongo-pass", default_config.MONGODB_SETTINGS[0]["password"]
            )
        finally:
            default_config.MONGODB_SETTINGS = original_settings
            importlib.reload(default_config)


class NotificationsTokenExceptionTestCase(BaseTestCase):
    def test_send_confirmation_email_token_exception(self):
        from webapp.notifications import send_confirmation_email

        recipient_email = "foo@bar.baz"
        with patch("webapp.notifications.utils.get_timed_serializer") as mock_ts:
            mock_ts.return_value.dumps.side_effect = RuntimeError("boom")
            success, message = send_confirmation_email(recipient_email)
        self.assertFalse(success)
        self.assertIn("Token inválido", message)

    def test_send_reset_password_email_token_exception(self):
        from webapp.notifications import send_reset_password_email

        recipient_email = "foo@bar.baz"
        with patch("webapp.notifications.utils.get_timed_serializer") as mock_ts:
            mock_ts.return_value.dumps.side_effect = RuntimeError("boom")
            success, message = send_reset_password_email(recipient_email)
        self.assertFalse(success)
        self.assertIn("Token inválido", message)
