# coding: utf-8

import datetime
from unittest.mock import Mock, patch

from flask import current_app, url_for
from werkzeug.exceptions import NotFound

from webapp import choices
from webapp.main import custom_filters
from webapp.utils.utils import create_user

from .base import BaseTestCase


class MainHelperCoverageTestCase(BaseTestCase):
    API_EMAIL = "helpers-coverage@opac.org"
    API_PASSWORD = "helpers-coverage-password"

    def _journal_url(self):
        return url_for("restapi.journal")

    def test_token_required_missing_token(self):
        with self.client as client:
            response = client.post(self._journal_url(), json={})
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertEqual(data["message"], "token is missing")
        self.assertEqual(data["data"], [])

    def test_token_required_invalid_token(self):
        with self.client as client:
            response = client.post(
                f"{self._journal_url()}?token=not-a-valid-jwt",
                json={},
            )
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertEqual(data["message"], "token is invalid or expired")
        self.assertEqual(data["data"], [])

    def test_token_required_valid_token(self):
        create_user(self.API_EMAIL, self.API_PASSWORD, True)
        with self.client as client:
            auth_response = client.post(
                url_for("restapi.authenticate"),
                auth=(self.API_EMAIL, self.API_PASSWORD),
            )
            token = auth_response.get_json()["token"]
            response = client.post(
                f"{self._journal_url()}?token={token}",
                json={"id": "1678-4464"},
            )
        self.assertNotEqual(response.status_code, 401)

    def test_auth_missing_credentials(self):
        with self.client as client:
            response = client.post(url_for("restapi.authenticate"))
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertEqual(data["message"], "could not verify")

    def test_auth_missing_username(self):
        with self.client as client:
            response = client.post(
                url_for("restapi.authenticate"),
                auth=("", self.API_PASSWORD),
            )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.get_json()["message"],
            "could not verify",
        )

    def test_auth_missing_password(self):
        with self.client as client:
            response = client.post(
                url_for("restapi.authenticate"),
                auth=(self.API_EMAIL, ""),
            )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.get_json()["message"],
            "could not verify",
        )

    def test_auth_user_not_found(self):
        with self.client as client:
            response = client.post(
                url_for("restapi.authenticate"),
                auth=("unknown-user@opac.org", "any-password"),
            )
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertEqual(data["message"], "user not found")
        self.assertEqual(data["data"], [])

    def test_auth_wrong_password(self):
        create_user(self.API_EMAIL, self.API_PASSWORD, True)
        with self.client as client:
            response = client.post(
                url_for("restapi.authenticate"),
                auth=(self.API_EMAIL, "wrong-password"),
            )
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertEqual(data["message"], "could not verify")

    def test_auth_success(self):
        create_user(self.API_EMAIL, self.API_PASSWORD, True)
        with self.client as client:
            response = client.post(
                url_for("restapi.authenticate"),
                auth=(self.API_EMAIL, self.API_PASSWORD),
            )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["message"], "Validated successfully")
        self.assertIn("token", data)
        self.assertIn("exp", data)

    @patch("webapp.main.errors.jsonify")
    def test_page_not_found_json_handler(self, mock_jsonify):
        mock_response = Mock()
        mock_jsonify.return_value = mock_response
        exc = NotFound("page not found")

        with current_app.test_request_context(
            "/page_not_found",
            headers={"Accept": "application/json"},
        ):
            from webapp.main.errors import page_not_found

            response = page_not_found(exc)

        mock_jsonify.assert_called_once_with({"error": exc})
        self.assertEqual(mock_response.status_code, 404)
        self.assertIs(response, mock_response)


class MainCustomFiltersCoverageTestCase(BaseTestCase):
    def test_trans_alpha2_known_code(self):
        self.assertEqual(
            custom_filters.trans_alpha2("pt"),
            choices.ISO3166_ALPHA2["pt"],
        )

    def test_trans_alpha2_unknown_code_returns_value(self):
        self.assertEqual(custom_filters.trans_alpha2("xx"), "xx")

    def test_trans_alpha2_none_returns_none(self):
        self.assertIsNone(custom_filters.trans_alpha2(None))

    def test_trans_alpha2_empty_string_returns_empty(self):
        self.assertEqual(custom_filters.trans_alpha2(""), "")

    def test_datetimefilter_formats_utc_datetime(self):
        value = datetime.datetime(2020, 6, 15, 12, 30, tzinfo=datetime.timezone.utc)
        with current_app.app_context():
            result = custom_filters.datetimefilter(value, "%Y-%m-%d")
        self.assertRegex(result, r"^\d{4}-\d{2}-\d{2}$")

    def test_datetimefilter_default_format(self):
        value = datetime.datetime(2020, 6, 15, 12, 30, tzinfo=datetime.timezone.utc)
        with current_app.app_context():
            result = custom_filters.datetimefilter(value)
        self.assertRegex(result, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")

    def test_datetimefilter_invalid_value_raises(self):
        with current_app.app_context():
            with self.assertRaises(AttributeError):
                custom_filters.datetimefilter(None)

    def test_make_absolute_url_empty_base_url_branch(self):
        self.assertEqual(
            custom_filters.make_absolute_url("media/logo.png", ""),
            "media/logo.png",
        )
