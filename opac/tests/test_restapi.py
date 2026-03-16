import base64
import datetime
import json
import os
from unittest.mock import Mock, patch
from urllib.parse import quote

from flask import current_app, url_for
from flask_babelex import gettext as _
from opac_schema.v1 import models
from webapp import dbsql
from webapp.controllers import get_user_by_email
from webapp.utils import create_user

# Garante que o modelo User (e demais) esteja registrado em dbsql antes dos testes de API que usam create_user
import webapp.models  # noqa: F401

from .base import BaseTestCase
from .utils import makeOneArticle, makeOneJournal


FIXTURES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

# Credenciais usadas nos testes da API (endpoints exigem @helper.token_required)
API_TEST_USER_EMAIL = "api_test@example.com"
API_TEST_USER_PASSWORD = "api_test_password"


def _get_api_token(client):
    """Cria um usuário de teste (se não existir), autentica via POST /api/v1/auth e retorna o token."""
    dbsql.create_all()
    if get_user_by_email(API_TEST_USER_EMAIL) is None:
        create_user(API_TEST_USER_EMAIL, API_TEST_USER_PASSWORD, True)
    auth_response = client.post(
        url_for("restapi.authenticate"),
        data=json.dumps({}),
        headers={
            "Authorization": "Basic %s"
            % base64.b64encode(
                ("%s:%s" % (API_TEST_USER_EMAIL, API_TEST_USER_PASSWORD)).encode()
            ).decode()
        },
        content_type="application/json",
    )
    assert auth_response.status_code == 200, auth_response.data
    data = auth_response.get_json()
    token = data.get("token")
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def _url_with_token(url, token):
    """Adiciona o parâmetro token à URL (query string). Token é codificado para evitar corromper +, /, = do JWT."""
    sep = "&" if "?" in url else "?"
    return "%s%stoken=%s" % (url, sep, quote(token, safe=""))


class RestAPIJournalTestCase(BaseTestCase):
    def load_json_fixture(self, filename):
        with open(os.path.join(FIXTURES_PATH, filename)) as f:
            return json.load(f)

    def setUp(self):
        self.journal_dict = self.load_json_fixture("journal_payload.json")

    def test_add_journal_by_api(self):
        with current_app.app_context():
            with self.client as client:
                token = _get_api_token(client)
                response = client.post(
                    _url_with_token(url_for("restapi.journal"), token),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

    def test_add_journal_by_api_without_data(self):
        with current_app.app_context():
            with self.client as client:
                token = _get_api_token(client)
                response = client.post(
                    _url_with_token(url_for("restapi.journal"), token),
                    data=json.dumps({}),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 500)
            data = response.get_json()
            self.assertTrue(data.get("failed"))
            err = (data.get("error") or "").lower()
            self.assertTrue(
                "journal" in err or "is_public" in err,
                msg="Expected error about journal or is_public, got: %s" % data.get("error"),
            )

    def test_add_journal_by_api_without_id(self):
        del self.journal_dict["id"]

        with current_app.app_context():
            with self.client as client:
                token = _get_api_token(client)
                response = client.post(
                    _url_with_token(url_for("restapi.journal"), token),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
            self.assertEqual(response.status_code, 500)
            data = response.get_json()
            self.assertTrue(data.get("failed"))
            err = data.get("error", "")
            self.assertTrue(
                "Field is required" in err or "'is_public'" in err or "Journal:None" in err,
                msg="Expected validation or is_public error, got: %s" % err,
            )

    def test_add_journal_by_api_with_wrong_data(self):
        del self.journal_dict["status_history"][0]["date"]

        with current_app.app_context():
            with self.client as client:
                token = _get_api_token(client)
                response = client.post(
                    _url_with_token(url_for("restapi.journal"), token),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
            self.assertEqual(response.status_code, 500)
            data = response.get_json()
            self.assertTrue(data.get("failed"))
            err = data.get("error", "")
            self.assertTrue(
                "timeline" in err or "'is_public'" in err or "since.cannot" in err,
                msg="Expected timeline or is_public error, got: %s" % err,
            )


class RestAPIIssueTestCase(BaseTestCase):
    def load_json_fixture(self, filename):
        with open(os.path.join(FIXTURES_PATH, filename)) as f:
            return json.load(f)

    def setUp(self):
        self.journal_dict = self.load_json_fixture("journal_payload.json")
        self.issue_dict = self.load_json_fixture("issue_payload.json")

    def test_add_issue_by_api(self):
        with current_app.app_context():
            with self.client as client:
                token = _get_api_token(client)
                # journal
                response = client.post(
                    _url_with_token(url_for("restapi.journal"), token),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

                # issue
                response = client.post(
                    _url_with_token(
                        url_for("restapi.issue")
                        + "?journal_id="
                        + self.journal_dict.get("id"),
                        token,
                    ),
                    data=json.dumps(self.issue_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.data, b'{"failed":false,"id":"1678-4464-1998-v29-n3"}\n'
            )

    def test_add_issue_by_api_without_data(self):
        with current_app.app_context():
            with self.client as client:
                token = _get_api_token(client)
                # journal
                response = client.post(
                    _url_with_token(url_for("restapi.journal"), token),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

                # issue
                response = client.post(
                    _url_with_token(
                        url_for("restapi.issue")
                        + "?journal_id="
                        + self.journal_dict.get("id"),
                        token,
                    ),
                    data=json.dumps({}),
                    follow_redirects=True,
                    content_type="application/json",
                )
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.data, b'{"error":"\'id\'","failed":true}\n')

    def test_add_issue_by_api_without_journal_id(self):
        with current_app.app_context():
            with self.client as client:
                token = _get_api_token(client)
                # journal
                response = client.post(
                    _url_with_token(url_for("restapi.journal"), token),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

                # issue (sem journal_id)
                response = client.post(
                    _url_with_token(url_for("restapi.issue"), token),
                    data=json.dumps({}),
                    follow_redirects=True,
                    content_type="application/json",
                )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(
                response.data, b'{"error":"missing param journal_id","failed":true}\n'
            )


class RestAPIAricleTestCase(BaseTestCase):
    def load_json_fixture(self, filename):
        with open(os.path.join(FIXTURES_PATH, filename)) as f:
            return json.load(f)

    def setUp(self):
        self.journal_dict = self.load_json_fixture("journal_payload.json")
        self.issue_dict = self.load_json_fixture("issue_payload.json")
        self.article_dict = self.load_json_fixture("article_payload.json")

    def test_add_article_by_api(self):
        with current_app.app_context():
            with self.client as client:
                token = _get_api_token(client)
                # journal
                response = client.post(
                    _url_with_token(url_for("restapi.journal"), token),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

                # issue
                response = client.post(
                    _url_with_token(
                        url_for("restapi.issue")
                        + "?journal_id="
                        + self.journal_dict.get("id"),
                        token,
                    ),
                    data=json.dumps(self.issue_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.data, b'{"failed":false,"id":"1678-4464-1998-v29-n3"}\n'
                )

                # article
                article_url = (
                    url_for("restapi.article")
                    + "?issue_id=%s&article_id=%s&order=%s&article_url=%s"
                    % (
                        self.issue_dict.get("id"),
                        "id_test",
                        1,
                        "http://minio.scielo.org/documentstore/example.xml",
                    )
                )
                response = client.post(
                    _url_with_token(article_url, token),
                    data=json.dumps(self.article_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"id_test"}\n')

            # check if the article is in database
            self.assertTrue(models.Article.objects.get(_id="id_test"))

    def test_add_article_by_api_without_data(self):
        with current_app.app_context():
            with self.client as client:
                token = _get_api_token(client)
                response = client.post(
                    _url_with_token(url_for("restapi.journal"), token),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

                response = client.post(
                    _url_with_token(
                        url_for("restapi.issue")
                        + "?journal_id="
                        + self.journal_dict.get("id"),
                        token,
                    ),
                    data=json.dumps(self.issue_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.data, b'{"failed":false,"id":"1678-4464-1998-v29-n3"}\n'
                )

                article_url = (
                    url_for("restapi.article")
                    + "?issue_id=%s&article_id=%s&order=%s&article_url=%s"
                    % (
                        self.issue_dict.get("id"),
                        "id_test",
                        1,
                        "http://minio.scielo.org/documentstore/example.xml",
                    )
                )
                response = client.post(
                    _url_with_token(article_url, token),
                    data=json.dumps({}),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"id_test"}\n')

            # check if the article is in database
            self.assertTrue(models.Article.objects.get(_id="id_test"))

    def test_add_article_by_api_without_issue_id(self):
        with current_app.app_context():
            with self.client as client:
                token = _get_api_token(client)
                response = client.post(
                    _url_with_token(url_for("restapi.journal"), token),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

                response = client.post(
                    _url_with_token(
                        url_for("restapi.issue")
                        + "?journal_id="
                        + self.journal_dict.get("id"),
                        token,
                    ),
                    data=json.dumps(self.issue_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.data, b'{"failed":false,"id":"1678-4464-1998-v29-n3"}\n'
                )

                article_url = (
                    url_for("restapi.article")
                    + "?article_id=%s&order=%s&article_url=%s"
                    % (
                        "id_test",
                        1,
                        "http://minio.scielo.org/documentstore/example.xml",
                    )
                )
                response = client.post(
                    _url_with_token(article_url, token),
                    data=json.dumps(self.article_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data, b'{"error":"missing param issue_id","failed":true}\n')

            with self.assertRaises(models.Article.DoesNotExist):
                models.Article.objects.get(_id="id_test")

    def test_add_article_by_api_without_article_id(self):
        with current_app.app_context():
            with self.client as client:
                token = _get_api_token(client)
                response = client.post(
                    _url_with_token(url_for("restapi.journal"), token),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

                response = client.post(
                    _url_with_token(
                        url_for("restapi.issue")
                        + "?journal_id="
                        + self.journal_dict.get("id"),
                        token,
                    ),
                    data=json.dumps(self.issue_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.data, b'{"failed":false,"id":"1678-4464-1998-v29-n3"}\n'
                )

                article_url = (
                    url_for("restapi.article")
                    + "?issue_id=%s&order=%s&article_url=%s"
                    % (
                        self.issue_dict.get("id"),
                        1,
                        "http://minio.scielo.org/documentstore/example.xml",
                    )
                )
                response = client.post(
                    _url_with_token(article_url, token),
                    data=json.dumps({}),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data, b'{"error":"missing param article_id","failed":true}\n')

            with self.assertRaises(models.Article.DoesNotExist):
                models.Article.objects.get(_id="id_test")

    def test_add_article_by_api_without_order(self):
        with current_app.app_context():
            with self.client as client:
                token = _get_api_token(client)
                response = client.post(
                    _url_with_token(url_for("restapi.journal"), token),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

                response = client.post(
                    _url_with_token(
                        url_for("restapi.issue")
                        + "?journal_id="
                        + self.journal_dict.get("id"),
                        token,
                    ),
                    data=json.dumps(self.issue_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.data, b'{"failed":false,"id":"1678-4464-1998-v29-n3"}\n'
                )

                article_url = (
                    url_for("restapi.article")
                    + "?issue_id=%s&article_id=%s&article_url=%s"
                    % (
                        self.issue_dict.get("id"),
                        "id_test",
                        "http://minio.scielo.org/documentstore/example.xml",
                    )
                )
                response = client.post(
                    _url_with_token(article_url, token),
                    data=json.dumps(self.article_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data, b'{"error":"missing param order","failed":true}\n')

            with self.assertRaises(models.Article.DoesNotExist):
                models.Article.objects.get(_id="id_test")


class RestAPIIssueSyncTestCase(BaseTestCase):

    def setUp(self):
        # Exemplos de dados para os testes
        self.issue_id = "0001-3765-2000-v72-n1"
        self.articles_id_payload = [
            "hYnMxt6qc7qsHQtZqMcgYmv",
            "wNZLxRjKfGdDw8KGmbNN7qj"
        ]
        self.issue_mock = Mock()
        self.issue_mock.id = self.issue_id  

    @patch("webapp.controllers.get_issue_by_iid")
    @patch("webapp.controllers.delete_articles_by_iid")
    def test_sync_articles_removed(
        self, mock_delete_articles_by_iid, mock_get_issue_by_iid
    ):
        mock_get_issue_by_iid.return_value = self.issue_mock
        mock_delete_articles_by_iid.return_value = ["article_to_remove"]

        with current_app.app_context():
            with self.client as client:
                token = _get_api_token(client)
                resp = client.post(
                    _url_with_token(url_for("restapi.issue_sync"), token),
                    data=json.dumps({
                        "issue_id": self.issue_id,
                        "articles_id": self.articles_id_payload
                    }),
                    content_type="application/json"
                )
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data.get("failed"), False)
        self.assertEqual(data.get("removed_articles"), ["article_to_remove"])

    @patch("webapp.controllers.get_issue_by_iid")
    @patch("webapp.controllers.delete_articles_by_iid")
    def test_sync_no_articles_removed(
        self, mock_delete_articles_by_iid, mock_get_issue_by_iid
    ):
        mock_get_issue_by_iid.return_value = self.issue_mock
        mock_delete_articles_by_iid.return_value = []

        with current_app.app_context():
            with self.client as client:
                token = _get_api_token(client)
                resp = client.post(
                    _url_with_token(url_for("restapi.issue_sync"), token),
                    data=json.dumps({
                        "issue_id": self.issue_id,
                        "articles_id": self.articles_id_payload
                    }),
                    content_type="application/json"
                )
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data.get("failed"), False)
        self.assertEqual(data.get("removed_articles"), [])

    @patch("webapp.main.views.request")
    def test_sync_missing_issue_id_or_articles_id(self, mock_request):
        # 1) Payload vazio: simula get_json() retornando {} → view deve retornar 400
        mock_request.get_json.return_value = {}
        with current_app.app_context():
            with self.client as client:
                token = _get_api_token(client)
                resp = client.post(
                    _url_with_token(url_for("restapi.issue_sync"), token),
                    data=json.dumps({}),
                    content_type="application/json",
                )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json() or {}
        self.assertTrue(data.get("failed"))
        self.assertIn("missing param", (data.get("error") or ""))

        # 2) Só issue_id (issue pode não existir → 404) ou validação → 400
        mock_request.get_json.return_value = {"issue_id": self.issue_id}
        with current_app.app_context():
            with self.client as client:
                token = _get_api_token(client)
                resp = client.post(
                    _url_with_token(url_for("restapi.issue_sync"), token),
                    data=json.dumps({"issue_id": self.issue_id}),
                    content_type="application/json",
                )
        self.assertIn(resp.status_code, (400, 404))
        if resp.status_code == 400:
            self.assertTrue((resp.get_json() or {}).get("failed"))

        # 3) Só articles_id (falta issue_id): simula payload sem issue_id → 400
        mock_request.get_json.return_value = {"articles_id": self.articles_id_payload}
        with current_app.app_context():
            with self.client as client:
                token = _get_api_token(client)
                resp = client.post(
                    _url_with_token(url_for("restapi.issue_sync"), token),
                    data=json.dumps({"articles_id": self.articles_id_payload}),
                    content_type="application/json",
                )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json() or {}
        self.assertTrue(data.get("failed"))

    @patch("webapp.controllers.get_issue_by_iid")
    def test_sync_issue_not_found(self, mock_get_issue_by_iid):
        mock_get_issue_by_iid.return_value = None
        with current_app.app_context():
            with self.client as client:
                token = _get_api_token(client)
                resp = client.post(
                    _url_with_token(url_for("restapi.issue_sync"), token),
                    data=json.dumps({
                        "issue_id": "not-found",
                        "articles_id": self.articles_id_payload
                    }),
                    content_type="application/json"
                )
        data = resp.get_json()
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(data.get("failed"), True)
        self.assertEqual(data.get("error"), "issue not found")


class RestAPICounterDictTestCase(BaseTestCase):

    def test_counter_dict_filter_by_journal_id(self):
        """Test that counter_dict returns only articles for the given journal_id."""
        with current_app.app_context():
            journal_a = makeOneJournal({"_id": "1111-1111", "acronym": "jrn-a"})
            journal_b = makeOneJournal({"_id": "2222-2222", "acronym": "jrn-b"})

            now = datetime.datetime.now()
            makeOneArticle({
                "_id": "art-a1",
                "aid": "art-a1",
                "journal": journal_a,
                "updated": now,
            })
            makeOneArticle({
                "_id": "art-b1",
                "aid": "art-b1",
                "journal": journal_b,
                "updated": now,
            })

            with self.client as client:
                response = client.get(
                    url_for("restapi.router_counter_dicts", journal_id="1111-1111"),
                    follow_redirects=True,
                )
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertEqual(data["total"], 1)
                self.assertIn("art-a1", data["documents"])
                self.assertNotIn("art-b1", data["documents"])

    def test_counter_dict_without_journal_id_returns_all(self):
        """Test that counter_dict returns all articles when no journal_id is provided."""
        with current_app.app_context():
            journal_a = makeOneJournal({"_id": "1111-1111", "acronym": "jrn-a"})
            journal_b = makeOneJournal({"_id": "2222-2222", "acronym": "jrn-b"})

            now = datetime.datetime.now()
            makeOneArticle({
                "_id": "art-a1",
                "aid": "art-a1",
                "journal": journal_a,
                "updated": now,
            })
            makeOneArticle({
                "_id": "art-b1",
                "aid": "art-b1",
                "journal": journal_b,
                "updated": now,
            })

            with self.client as client:
                response = client.get(
                    url_for("restapi.router_counter_dicts"),
                    follow_redirects=True,
                )
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertEqual(data["total"], 2)
                self.assertIn("art-a1", data["documents"])
                self.assertIn("art-b1", data["documents"])

    def test_counter_dict_filter_by_nonexistent_journal_id(self):
        """Test that counter_dict returns no articles for a non-existent journal_id."""
        with current_app.app_context():
            journal_a = makeOneJournal({"_id": "1111-1111", "acronym": "jrn-a"})

            now = datetime.datetime.now()
            makeOneArticle({
                "_id": "art-a1",
                "aid": "art-a1",
                "journal": journal_a,
                "updated": now,
            })

            with self.client as client:
                response = client.get(
                    url_for("restapi.router_counter_dicts", journal_id="9999-9999"),
                    follow_redirects=True,
                )
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertEqual(data["total"], 0)
                self.assertEqual(data["documents"], {})
