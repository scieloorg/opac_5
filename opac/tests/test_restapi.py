import datetime
import json
import os
from unittest.mock import Mock, patch

from flask import current_app, url_for
from flask_babel import gettext as _
from opac_schema.v1 import models

from .base import BaseTestCase
from .utils import makeOneArticle, makeOneJournal


FIXTURES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


class RestAPIAuthMixin:
    API_EMAIL = "restapi-user@opac.org"
    API_PASSWORD = "restapi-test-password"

    def setUp(self):
        super().setUp()
        self._api_token = None

    def _get_api_token(self, client):
        if self._api_token is None:
            from webapp.utils.utils import create_user

            create_user(self.API_EMAIL, self.API_PASSWORD, True)
            response = client.post(
                url_for("restapi.authenticate"),
                auth=(self.API_EMAIL, self.API_PASSWORD),
            )
            self._api_token = response.get_json()["token"]
        return self._api_token

    def _api_post(self, client, endpoint, data, follow_redirects=True, **query):
        query["token"] = self._get_api_token(client)
        return client.post(
            url_for(endpoint, **query),
            data=json.dumps(data),
            follow_redirects=follow_redirects,
            content_type="application/json",
        )


class RestAPIJournalTestCase(RestAPIAuthMixin, BaseTestCase):
    def load_json_fixture(self, filename):
        with open(os.path.join(FIXTURES_PATH, filename)) as f:
            return json.load(f)

    def setUp(self):
        super().setUp()
        self.journal_dict = self.load_json_fixture("journal_payload.json")

    def test_add_journal_by_api(self):
        with current_app.app_context():
            with self.client as client:
                response = self._api_post(client, "restapi.journal", self.journal_dict)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

    def test_add_journal_by_api_without_data(self):
        with current_app.app_context():
            with self.client as client:
                response = self._api_post(client, "restapi.journal", {})

            self.assertEqual(response.status_code, 500)
            self.assertEqual(
                response.data,
                b'{"error":"\'is_public\'","failed":true}\n',
            )

    def test_add_journal_by_api_without_id(self):
        del self.journal_dict["id"]

        with current_app.app_context():
            with self.client as client:
                response = self._api_post(client, "restapi.journal", self.journal_dict)
            self.assertEqual(response.status_code, 500)
            self.assertEqual(
                response.data,
                b'{"error":"ValidationError (Journal:None) (Field is required: [\'_id\', \'jid\'])","failed":true}\n',
            )

    def test_add_journal_by_api_with_wrong_data(self):
        del self.journal_dict["status_history"][0]["date"]

        with current_app.app_context():
            with self.client as client:
                response = self._api_post(client, "restapi.journal", self.journal_dict)
            self.assertEqual(response.status_code, 500)
            self.assertEqual(
                response.data,
                b'{"error":"ValidationError (Journal:1678-4464) (since.cannot parse date \\"\\": [\'timeline\'])","failed":true}\n',
            )


class RestAPIIssueTestCase(RestAPIAuthMixin, BaseTestCase):
    def load_json_fixture(self, filename):
        with open(os.path.join(FIXTURES_PATH, filename)) as f:
            return json.load(f)

    def setUp(self):
        super().setUp()
        self.journal_dict = self.load_json_fixture("journal_payload.json")
        self.issue_dict = self.load_json_fixture("issue_payload.json")

    def test_add_issue_by_api(self):
        with current_app.app_context():
            # journal
            with self.client as client:
                response = self._api_post(client, "restapi.journal", self.journal_dict)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

            # issue
            with self.client as client:
                response = self._api_post(client, "restapi.issue", self.issue_dict, journal_id=self.journal_dict.get("id"))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.data, b'{"failed":false,"id":"1678-4464-1998-v29-n3"}\n'
            )

    def test_add_issue_by_api_updates_by_pid_when_id_changes(self):
        with current_app.app_context():
            with self.client as client:
                self._api_post(client, "restapi.journal", self.journal_dict)
                response = self._api_post(
                    client,
                    "restapi.issue",
                    self.issue_dict,
                    journal_id=self.journal_dict.get("id"),
                )
            self.assertEqual(response.status_code, 200)

            old_id = self.issue_dict["id"]
            article = makeOneArticle({"journal": self.journal_dict["id"], "issue": old_id})

            payload = dict(self.issue_dict)
            payload["id"] = "1678-4464-1998-v29"
            payload["number"] = None

            with self.client as client:
                response = self._api_post(
                    client,
                    "restapi.issue",
                    payload,
                    journal_id=self.journal_dict.get("id"),
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.data, b'{"failed":false,"id":"1678-4464-1998-v29"}\n'
            )
            article.reload()
            self.assertEqual(article.issue.id, "1678-4464-1998-v29")
            self.assertEqual(
                models.Issue.objects.filter(pid=payload["pid"]).count(), 1
            )
            self.assertIsNone(models.Issue.objects.filter(_id=old_id).first())

    def test_add_issue_by_api_without_data(self):
        with current_app.app_context():
            # journal
            with self.client as client:
                response = self._api_post(client, "restapi.journal", self.journal_dict)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

            # issue
            with self.client as client:
                response = self._api_post(client, "restapi.issue", {}, journal_id=self.journal_dict.get("id"))

            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.data, b'{"error":"\'id\'","failed":true}\n')

    def test_add_issue_by_api_without_journal_id(self):
        with current_app.app_context():
            # journal
            with self.client as client:
                response = self._api_post(client, "restapi.journal", self.journal_dict)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

            # issue
            with self.client as client:
                response = self._api_post(client, "restapi.issue", {})

            self.assertEqual(response.status_code, 400)
            self.assertEqual(
                response.data, b'{"error":"missing param journal_id","failed":true}\n'
            )


class RestAPIAricleTestCase(RestAPIAuthMixin, BaseTestCase):
    def load_json_fixture(self, filename):
        with open(os.path.join(FIXTURES_PATH, filename)) as f:
            return json.load(f)

    def setUp(self):
        super().setUp()
        self.journal_dict = self.load_json_fixture("journal_payload.json")
        self.issue_dict = self.load_json_fixture("issue_payload.json")
        self.article_dict = self.load_json_fixture("article_payload.json")

    def test_add_article_by_api(self):
        with current_app.app_context():
            # journal
            with self.client as client:
                response = self._api_post(client, "restapi.journal", self.journal_dict)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

            # issue
            with self.client as client:
                response = self._api_post(client, "restapi.issue", self.issue_dict, journal_id=self.journal_dict.get("id"))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.data, b'{"failed":false,"id":"1678-4464-1998-v29-n3"}\n'
            )

            # article
            with self.client as client:
                response = self._api_post(
                    client,
                    "restapi.article",
                    self.article_dict,
                    issue_id=self.issue_dict.get("id"),
                    article_id="id_test",
                    order=1,
                    article_url="http://minio.scielo.org/documentstore/example.xml",
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"id_test"}\n')

            # check if the article is in database
            self.assertTrue(models.Article.objects.get(_id="id_test"))

    def test_add_article_by_api_without_data(self):
        with current_app.app_context():
            # journal
            with self.client as client:
                response = self._api_post(client, "restapi.journal", self.journal_dict)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

            # issue
            with self.client as client:
                response = self._api_post(client, "restapi.issue", self.issue_dict, journal_id=self.journal_dict.get("id"))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.data, b'{"failed":false,"id":"1678-4464-1998-v29-n3"}\n'
            )

            # article
            with self.client as client:
                response = self._api_post(
                    client,
                    "restapi.article",
                    {},
                    issue_id=self.issue_dict.get("id"),
                    article_id="id_test",
                    order=1,
                    article_url="http://minio.scielo.org/documentstore/example.xml",
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"id_test"}\n')
            
            # check if the article is in database
            self.assertTrue(models.Article.objects.get(_id="id_test"))

    def test_add_article_by_api_without_issue_id(self):
        with current_app.app_context():
            # journal
            with self.client as client:
                response = self._api_post(client, "restapi.journal", self.journal_dict)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

            # issue
            with self.client as client:
                response = self._api_post(client, "restapi.issue", self.issue_dict, journal_id=self.journal_dict.get("id"))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.data, b'{"failed":false,"id":"1678-4464-1998-v29-n3"}\n'
            )

            # article
            with self.client as client:
                response = self._api_post(
                    client,
                    "restapi.article",
                    self.article_dict,
                    article_id="id_test",
                    order=1,
                    article_url="http://minio.scielo.org/documentstore/example.xml",
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
                response = self._api_post(client, "restapi.journal", self.journal_dict)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

            # issue
            with self.client as client:
                response = self._api_post(client, "restapi.issue", self.issue_dict, journal_id=self.journal_dict.get("id"))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.data, b'{"failed":false,"id":"1678-4464-1998-v29-n3"}\n'
            )

            # article
            with self.client as client:
                response = self._api_post(
                    client,
                    "restapi.article",
                    {},
                    issue_id=self.issue_dict.get("id"),
                    order=1,
                    article_url="http://minio.scielo.org/documentstore/example.xml",
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
                response = self._api_post(client, "restapi.journal", self.journal_dict)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'{"failed":false,"id":"1678-4464"}\n')

            # issue
            with self.client as client:
                response = self._api_post(client, "restapi.issue", self.issue_dict, journal_id=self.journal_dict.get("id"))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.data, b'{"failed":false,"id":"1678-4464-1998-v29-n3"}\n'
            )

            # article
            with self.client as client:
                response = self._api_post(
                    client,
                    "restapi.article",
                    self.article_dict,
                    issue_id=self.issue_dict.get("id"),
                    article_id="id_test",
                    article_url="http://minio.scielo.org/documentstore/example.xml",
                )

            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data, b'{"error":"missing param order","failed":true}\n')
            
            # check if the article is in database
            with self.assertRaises(models.Article.DoesNotExist):
                models.Article.objects.get(_id="id_test")


class RestAPIIssueSyncTestCase(RestAPIAuthMixin, BaseTestCase):

    def setUp(self):
        super().setUp()
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

        with self.client as client:
            resp = self._api_post(client, "restapi.issue_sync", {
                    "issue_id": self.issue_id,
                    "articles_id": self.articles_id_payload
                }, follow_redirects=False)
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

        with self.client as client:
            resp = self._api_post(client, "restapi.issue_sync", {
                    "issue_id": self.issue_id,
                    "articles_id": self.articles_id_payload
                }, follow_redirects=False)
            data = resp.get_json()
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(data.get("failed"), False)
            self.assertEqual(data.get("removed_articles"), [])

    def test_sync_missing_issue_id_or_articles_id(self):
        with self.client as client:
            resp = self._api_post(client, "restapi.issue_sync", {}, follow_redirects=False)
            data = resp.get_json()
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(data.get("failed"), True)
            self.assertIn("missing param", data.get("error"))

        with self.client as client:
            resp = self._api_post(client, "restapi.issue_sync", {"issue_id": self.issue_id}, follow_redirects=False)
            data = resp.get_json()
            self.assertEqual(resp.status_code, 404)
            self.assertEqual(data.get("failed"), True)
            self.assertEqual(data.get("error"), "issue not found")

        with self.client as client:
            resp = self._api_post(client, "restapi.issue_sync", {"articles_id": self.articles_id_payload}, follow_redirects=False)
            data = resp.get_json()
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(data.get("failed"), True)

    @patch("webapp.controllers.get_issue_by_iid")
    def test_sync_issue_not_found(self, mock_get_issue_by_iid):
        mock_get_issue_by_iid.return_value = None
        with self.client as client:
            resp = self._api_post(client, "restapi.issue_sync", {
                    "issue_id": "not-found",
                    "articles_id": self.articles_id_payload
                }, follow_redirects=False)
            data = resp.get_json()
            self.assertEqual(resp.status_code, 404)
            self.assertEqual(data.get("failed"), True)
            self.assertEqual(data.get("error"), "issue not found")


class RestAPICounterDictTestCase(BaseTestCase):

    def test_counter_dict_filter_by_journal_acronym(self):
        """Test that counter_dict returns only articles for the given journal acronym."""
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
                    url_for("restapi.router_counter_dicts", journal="jrn-a"),
                    follow_redirects=True,
                )
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertEqual(data["total"], 1)
                self.assertIn("art-a1", data["documents"])
                self.assertNotIn("art-b1", data["documents"])

    def test_counter_dict_filter_by_nonexistent_journal_acronym(self):
        """Test that counter_dict returns no articles for a non-existent journal acronym."""
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
                    url_for("restapi.router_counter_dicts", journal="unknown"),
                    follow_redirects=True,
                )
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertEqual(data["total"], 0)
                self.assertEqual(data["documents"], {})

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


class RestAPICounterDictV2TestCase(BaseTestCase):

    def _make_articles(self):
        journal_a = makeOneJournal({"_id": "1111-1111", "acronym": "jrn-a"})
        journal_b = makeOneJournal({"_id": "2222-2222", "acronym": "jrn-b"})
        makeOneArticle({
            "_id": "art-a1",
            "aid": "art-a1",
            "journal": journal_a,
            "created": datetime.datetime(2024, 1, 10, 8, 0, 0, 123456),
            "updated": datetime.datetime(2024, 1, 31, 10, 30, 15, 654321),
        })
        makeOneArticle({
            "_id": "art-b1",
            "aid": "art-b1",
            "journal": journal_b,
            "created": datetime.datetime(2024, 1, 10, 8, 0, 0),
            "updated": datetime.datetime(2024, 1, 31, 10, 30, 16),
        })

    def test_counter_dict_v2_filters_by_datetime_with_seconds(self):
        with current_app.app_context():
            self._make_articles()
            with self.client as client:
                response = client.get(
                    url_for(
                        "restapi_v2.router_counter_dicts_v2",
                        begin_date="2024-01-31T10:30:00",
                        end_date="2024-01-31T10:30:15",
                    ),
                )
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                # art-a1 updated 10:30:15.654321 > end_date 10:30:15
                self.assertEqual(data["total"], 0)

                response = client.get(
                    url_for(
                        "restapi_v2.router_counter_dicts_v2",
                        begin_date="2024-01-31 10:30:00",
                        end_date="2024-01-31 10:30:16",
                    ),
                )
                data = response.get_json()
                self.assertEqual(data["total"], 2)
                self.assertEqual(data["begin_date"], "2024-01-31T10:30:00.000000")
                self.assertEqual(data["end_date"], "2024-01-31T10:30:16.000000")

    def test_counter_dict_v2_filters_by_datetime_with_microseconds(self):
        with current_app.app_context():
            # art-a1 updated 10:30:15.654321, armazenado como 10:30:15.654
            self._make_articles()
            with self.client as client:
                cases = (
                    # (begin_date, end_date, total esperado)
                    ("2024-01-31T10:30:15.654000", "2024-01-31T10:30:15.654000", 1),
                    ("2024-01-31T10:30:15.653999", "2024-01-31T10:30:15.654321", 1),
                    ("2024-01-31T10:30:15.654001", "2024-01-31T10:30:15.999999", 0),
                    ("2024-01-31T10:30:15.000000", "2024-01-31T10:30:15.653999", 0),
                )
                for begin, end, total in cases:
                    response = client.get(
                        url_for(
                            "restapi_v2.router_counter_dicts_v2",
                            begin_date=begin,
                            end_date=end,
                        ),
                    )
                    self.assertEqual(response.status_code, 200, (begin, end))
                    data = response.get_json()
                    self.assertEqual(data["total"], total, (begin, end))
                    self.assertEqual(data["begin_date"], begin)
                    self.assertEqual(data["end_date"], end)

    def test_counter_dict_v2_article_dates_are_iso_with_microseconds(self):
        with current_app.app_context():
            self._make_articles()
            with self.client as client:
                response = client.get(
                    url_for(
                        "restapi_v2.router_counter_dicts_v2",
                        begin_date="2024-01-01T00:00:00",
                        end_date="2024-02-01T00:00:00",
                        journal="jrn-a",
                    ),
                )
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertEqual(data["total"], 1)
                doc = data["documents"][0]
                self.assertEqual(doc["aid"], "art-a1")
                # MongoDB armazena datas com precisão de milissegundos
                self.assertEqual(doc["created"], "2024-01-10T08:00:00.123000")
                self.assertEqual(doc["updated"], "2024-01-31T10:30:15.654000")
                self.assertTrue(doc["is_public"])
                self.assertNotIn("status", doc)
                self.assertNotIn("create", doc)
                self.assertNotIn("update", doc)

    def test_counter_dict_v2_rejects_invalid_iso_date(self):
        with current_app.app_context():
            with self.client as client:
                for value in ("31/01/2024", "2024-13-01", "invalid"):
                    response = client.get(
                        url_for(
                            "restapi_v2.router_counter_dicts_v2",
                            begin_date=value,
                        ),
                    )
                    self.assertEqual(response.status_code, 400, value)
                    self.assertTrue(response.get_json()["failed"])

    def test_counter_dict_v2_accepts_python_iso_formats(self):
        with current_app.app_context():
            self._make_articles()
            with self.client as client:
                cases = (
                    # (begin_date, end_date, total esperado)
                    ("2024-01-31", "2024-02-01", 2),
                    ("2024-01-31T10:30", "2024-01-31T10:31", 2),
                    ("2024-01-31T10:30:15.700", "2024-01-31T10:30:16", 1),
                    # 13:30:00Z == 10:30:00-03:00
                    ("2024-01-31T10:30:00-03:00", "2024-01-31T13:30:16Z", 0),
                    ("2024-01-31T10:30:00+00:00", "2024-01-31T10:30:16+00:00", 2),
                )
                for begin, end, total in cases:
                    response = client.get(
                        url_for(
                            "restapi_v2.router_counter_dicts_v2",
                            begin_date=begin,
                            end_date=end,
                        ),
                    )
                    self.assertEqual(response.status_code, 200, (begin, end))
                    self.assertEqual(
                        response.get_json()["total"], total, (begin, end)
                    )

    def test_counter_dict_v2_converts_timezone_to_utc(self):
        with current_app.app_context():
            with self.client as client:
                response = client.get(
                    url_for(
                        "restapi_v2.router_counter_dicts_v2",
                        begin_date="2024-01-31T10:30:00-03:00",
                        end_date="2024-01-31T13:30:00-03:00",
                    ),
                )
                data = response.get_json()
                self.assertEqual(data["begin_date"], "2024-01-31T13:30:00.000000")
                self.assertEqual(data["end_date"], "2024-01-31T16:30:00.000000")

    def test_counter_dict_v2_documents_ordered_by_updated(self):
        with current_app.app_context():
            journal = makeOneJournal({"_id": "1111-1111", "acronym": "jrn-a"})
            # aid em ordem alfabética inversa à ordem de updated
            for aid, minute in (("art-c", 3), ("art-a", 1), ("art-b", 2)):
                makeOneArticle({
                    "_id": aid,
                    "aid": aid,
                    "pid": "pid-" + aid,
                    "journal": journal,
                    "updated": datetime.datetime(2024, 1, 31, 10, minute, 0),
                })
            with self.client as client:
                response = client.get(
                    url_for(
                        "restapi_v2.router_counter_dicts_v2",
                        begin_date="2024-01-31",
                        end_date="2024-02-01",
                    ),
                )
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertEqual(
                    [d["aid"] for d in data["documents"]],
                    ["art-a", "art-b", "art-c"],
                )

                response = client.get(
                    url_for(
                        "restapi_v2.router_counter_dicts_v2",
                        begin_date="2024-01-31",
                        end_date="2024-02-01",
                        limit=1,
                        page=3,
                    ),
                )
                data = response.get_json()
                self.assertEqual(
                    [d["aid"] for d in data["documents"]], ["art-c"]
                )

    def test_counter_dict_v2_documents_ordered_by_publication_date_and_pid(self):
        with current_app.app_context():
            journal = makeOneJournal({"_id": "1111-1111", "acronym": "jrn-a"})
            updated = datetime.datetime(2024, 1, 31, 10, 0, 0)
            # mesmo updated: desempata por publication_date e pid
            for aid, pid, publication_date in (
                ("art-1", "pid-b", "2023-05-01"),
                ("art-2", "pid-c", "2024-01-01"),
                ("art-3", "pid-a", "2023-05-01"),
            ):
                makeOneArticle({
                    "_id": aid,
                    "aid": aid,
                    "pid": pid,
                    "journal": journal,
                    "publication_date": publication_date,
                    "updated": updated,
                })
            with self.client as client:
                response = client.get(
                    url_for(
                        "restapi_v2.router_counter_dicts_v2",
                        begin_date="2024-01-31",
                        end_date="2024-02-01",
                    ),
                )
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertEqual(
                    [d["aid"] for d in data["documents"]],
                    ["art-3", "art-1", "art-2"],
                )

    def test_counter_dict_v2_rejects_begin_after_end(self):
        with current_app.app_context():
            with self.client as client:
                response = client.get(
                    url_for(
                        "restapi_v2.router_counter_dicts_v2",
                        begin_date="2024-02-01T00:00:00",
                        end_date="2024-01-01T00:00:00",
                    ),
                )
                self.assertEqual(response.status_code, 400)

    def test_counter_dict_v2_default_dates(self):
        with current_app.app_context():
            with self.client as client:
                response = client.get(
                    url_for("restapi_v2.router_counter_dicts_v2")
                )
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                end = datetime.datetime.fromisoformat(data["end_date"])
                self.assertEqual(data["begin_date"], "1900-01-01T00:00:00.000000")
                self.assertLess(
                    datetime.datetime.now() - end, datetime.timedelta(minutes=1)
                )
                self.assertEqual(data["dictionary_date"], data["end_date"])
