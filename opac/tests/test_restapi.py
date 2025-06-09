import json
import os
from unittest.mock import Mock, patch

from flask import current_app, url_for
from flask_babelex import gettext as _
from opac_schema.v1 import models

from .base import BaseTestCase


FIXTURES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


class RestAPIJournalTestCase(BaseTestCase):
    def load_json_fixture(self, filename):
        with open(os.path.join(FIXTURES_PATH, filename)) as f:
            return json.load(f)

    def setUp(self):
        self.journal_dict = self.load_json_fixture("journal_payload.json")

    def test_add_journal_by_api(self):
        with current_app.app_context():
            with self.client as client:
                response = client.post(
                    url_for("restapi.journal"),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

    def test_add_journal_by_api_without_data(self):
        with current_app.app_context():
            with self.client as client:
                response = client.post(
                    url_for("restapi.journal"),
                    data=json.dumps({}),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 500)
            self.assertEqual(
                response.data,
                b'{"error":"The journal is mandatory to mount the URL","failed":true}\n',
            )

    def test_add_journal_by_api_without_id(self):
        del self.journal_dict["id"]

        with current_app.app_context():
            with self.client as client:
                response = client.post(
                    url_for("restapi.journal"),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
            self.assertEqual(response.status_code, 500)
            self.assertEqual(
                response.data,
                b'{"error":"ValidationError (Journal:None) (Field is required: [\'_id\', \'jid\'])","failed":true}\n',
            )

    def test_add_journal_by_api_with_wrong_data(self):
        del self.journal_dict["status_history"][0]["date"]

        with current_app.app_context():
            with self.client as client:
                response = client.post(
                    url_for("restapi.journal"),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )
            self.assertEqual(response.status_code, 500)
            self.assertEqual(
                response.data,
                b'{"error":"ValidationError (Journal:1678-4464) (since.cannot parse date \\"\\": [\'timeline\'])","failed":true}\n',
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
            # journal
            with self.client as client:
                response = client.post(
                    url_for("restapi.journal"),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

            # issue
            with self.client as client:
                response = client.post(
                    url_for("restapi.issue")
                    + "?journal_id="
                    + self.journal_dict.get("id"),
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
            # journal
            with self.client as client:
                response = client.post(
                    url_for("restapi.journal"),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

            # issue
            with self.client as client:
                response = client.post(
                    url_for("restapi.issue")
                    + "?journal_id="
                    + self.journal_dict.get("id"),
                    data=json.dumps({}),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.data, b'{"error":"\'id\'","failed":true}\n')

    def test_add_issue_by_api_without_journal_id(self):
        with current_app.app_context():
            # journal
            with self.client as client:
                response = client.post(
                    url_for("restapi.journal"),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

            # issue
            with self.client as client:
                response = client.post(
                    url_for("restapi.issue"),
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
            # journal
            with self.client as client:
                response = client.post(
                    url_for("restapi.journal"),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

            # issue
            with self.client as client:
                response = client.post(
                    url_for("restapi.issue")
                    + "?journal_id="
                    + self.journal_dict.get("id"),
                    data=json.dumps(self.issue_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.data, b'{"failed":false,"id":"1678-4464-1998-v29-n3"}\n'
            )

            # article
            with self.client as client:
                response = client.post(
                    # Using query string to send the params:
                    # ``issue_id``, ``article_id``, ``order``, ``article_url``,
                    url_for("restapi.article")
                    + "?issue_id=%s&article_id=%s&order=%s&article_url=%s"
                    % (
                        self.issue_dict.get("id"),
                        "id_test",
                        1,
                        "http://minio.scielo.org/documentstore/example.xml",
                    ),
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
            # journal
            with self.client as client:
                response = client.post(
                    url_for("restapi.journal"),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

            # issue
            with self.client as client:
                response = client.post(
                    url_for("restapi.issue")
                    + "?journal_id="
                    + self.journal_dict.get("id"),
                    data=json.dumps(self.issue_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.data, b'{"failed":false,"id":"1678-4464-1998-v29-n3"}\n'
            )

            # article
            with self.client as client:
                response = client.post(
                    # Using query string to send the params:
                    # ``issue_id``, ``article_id``, ``order``, ``article_url``,
                    url_for("restapi.article")
                    + "?issue_id=%s&article_id=%s&order=%s&article_url=%s"
                    % (
                        self.issue_dict.get("id"),
                        "id_test",
                        1,
                        "http://minio.scielo.org/documentstore/example.xml",
                    ),
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
            # journal
            with self.client as client:
                response = client.post(
                    url_for("restapi.journal"),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

            # issue
            with self.client as client:
                response = client.post(
                    url_for("restapi.issue")
                    + "?journal_id="
                    + self.journal_dict.get("id"),
                    data=json.dumps(self.issue_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.data, b'{"failed":false,"id":"1678-4464-1998-v29-n3"}\n'
            )

            # article
            with self.client as client:
                response = client.post(
                    # Using query string to send the params:
                    # ``issue_id``, ``article_id``, ``order``, ``article_url``,
                    url_for("restapi.article")
                    + "?article_id=%s&order=%s&article_url=%s"
                    % (
                        "id_test",
                        1,
                        "http://minio.scielo.org/documentstore/example.xml",
                    ),
                    data=json.dumps(self.article_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data, b'{"error":"missing param issue_id","failed":true}\n')
            
            # check if the article is in database
            with self.assertRaises(models.Article.DoesNotExist):
                models.Article.objects.get(_id="id_test")

    def test_add_article_by_api_without_article_id(self):
        with current_app.app_context():
            # journal
            with self.client as client:
                response = client.post(
                    url_for("restapi.journal"),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

            # issue
            with self.client as client:
                response = client.post(
                    url_for("restapi.issue")
                    + "?journal_id="
                    + self.journal_dict.get("id"),
                    data=json.dumps(self.issue_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.data, b'{"failed":false,"id":"1678-4464-1998-v29-n3"}\n'
            )

            # article
            with self.client as client:
                response = client.post(
                    # Using query string to send the params:
                    # ``issue_id``, ``article_id``, ``order``, ``article_url``,
                    url_for("restapi.article")
                    + "?issue_id=%s&order=%s&article_url=%s"
                    % (
                        self.issue_dict.get("id"),
                        1,
                        "http://minio.scielo.org/documentstore/example.xml",
                    ),
                    data=json.dumps({}),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data, b'{"error":"missing param article_id","failed":true}\n')
            
            # check if the article is in database
            with self.assertRaises(models.Article.DoesNotExist):
                models.Article.objects.get(_id="id_test")

    def test_add_article_by_api_without_order(self):
        with current_app.app_context():
            # journal
            with self.client as client:
                response = client.post(
                    url_for("restapi.journal"),
                    data=json.dumps(self.journal_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

            # issue
            with self.client as client:
                response = client.post(
                    url_for("restapi.issue")
                    + "?journal_id="
                    + self.journal_dict.get("id"),
                    data=json.dumps(self.issue_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.data, b'{"failed":false,"id":"1678-4464-1998-v29-n3"}\n'
            )

            # article
            with self.client as client:
                response = client.post(
                    # Using query string to send the params:
                    # ``issue_id``, ``article_id``, ``order``, ``article_url``,
                    url_for("restapi.article")
                    + "?issue_id=%s&article_id=%s&article_url=%s"
                    % (
                        self.issue_dict.get("id"),
                        "id_test",
                        "http://minio.scielo.org/documentstore/example.xml",
                    ),
                    data=json.dumps(self.article_dict),
                    follow_redirects=True,
                    content_type="application/json",
                )

            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data, b'{"error":"missing param order","failed":true}\n')
            
            # check if the article is in database
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
        self.issue_mock.iid = self.issue_id

    @patch("webapp.controllers.get_issue_by_iid")
    @patch("webapp.controllers.get_articles_by_iid")
    @patch("webapp.controllers.delete_articles_by_aids")
    def test_sync_articles_removed(
        self, mock_delete_articles_by_aids, mock_get_articles_by_iid, mock_get_issue_by_iid
    ):
        # Mockando retorno dos controllers
        mock_get_issue_by_iid.return_value = self.issue_mock
        # Artigos atuais na base (um a mais do que na payload)
        mock_get_articles_by_iid.return_value = [
            Mock(aid="hYnMxt6qc7qsHQtZqMcgYmv"),
            Mock(aid="wNZLxRjKfGdDw8KGmbNN7qj"),
            Mock(aid="article_to_remove"),
        ]
        mock_delete_articles_by_aids.return_value = ["article_to_remove"]

        with self.client as client:
            resp = client.post(
                url_for("restapi.issue_sync"),
                data=json.dumps({
                    "issue_id": self.issue_id,
                    "articles_id": self.articles_id_payload
                }),
                content_type="application/json"
            )
            data = resp.get_json()
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(data.get("failed"), False)
            self.assertEqual(data.get("removed_count"), 1)
            self.assertIn("article_to_remove", data.get("removed_articles"))
            self.assertEqual(set(data["remaining_articles"]), set(self.articles_id_payload))
            self.assertEqual(data.get("issue_id"), self.issue_id)
            self.assertEqual("Sync completed. 1 articles removed, 2 remain.", data.get("message"))

    @patch("webapp.controllers.get_issue_by_iid")
    @patch("webapp.controllers.get_articles_by_iid")
    def test_sync_no_articles_removed(
        self, mock_get_articles_by_iid, mock_get_issue_by_iid
    ):
        mock_get_issue_by_iid.return_value = self.issue_mock
        # Nenhum artigo a remover
        mock_get_articles_by_iid.return_value = [
            Mock(aid=a) for a in self.articles_id_payload
        ]

        with self.client as client:
            resp = client.post(
                url_for("restapi.issue_sync"),
                data=json.dumps({
                    "issue_id": self.issue_id,
                    "articles_id": self.articles_id_payload
                }),
                content_type="application/json"
            )
            data = resp.get_json()
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(data.get("failed"), False)
            self.assertEqual(data.get("removed_count"), 0)
            self.assertEqual(data.get("removed_articles"), [])
            self.assertEqual(set(data.get("remaining_articles")), set(self.articles_id_payload))
            self.assertEqual(data.get("issue_id"), self.issue_id)
            self.assertEqual("Sync completed. No articles were removed. 2 remain.", data.get("message"))

    def test_sync_missing_issue_id_or_articles_id(self):
        with self.client as client:
            resp = client.post(
                url_for("restapi.issue_sync"),
                data=json.dumps({}),
                content_type="application/json"
            )
            data = resp.get_json()
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(data.get("failed"), True)
            self.assertIn("missing param", data.get("error"))

        with self.client as client:
            resp = client.post(
                url_for("restapi.issue_sync"),
                data=json.dumps({"issue_id": self.issue_id}),
                content_type="application/json"
            )
            data = resp.get_json()
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(data.get("failed"), True)

        with self.client as client:
            resp = client.post(
                url_for("restapi.issue_sync"),
                data=json.dumps({"articles_id": self.articles_id_payload}),
                content_type="application/json"
            )
            data = resp.get_json()
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(data.get("failed"), True)

    @patch("webapp.controllers.get_issue_by_iid")
    def test_sync_issue_not_found(self, mock_get_issue_by_iid):
        mock_get_issue_by_iid.return_value = None
        with self.client as client:
            resp = client.post(
                url_for("restapi.issue_sync"),
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