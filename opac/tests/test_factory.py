# coding: utf-8
import json
import os
from unittest.mock import patch

from exceptions import PublishDocumentError
from flask import current_app
from opac_schema.v1 import models

from webapp.factory import (
    ArticleFactory,
    AuxiliarArticleFactory,
    IssueFactory,
    JournalFactory,
    _format_author_name,
    _get_issue_for_upsert,
    isoformat_to_datetime,
)

from .base import BaseTestCase
from . import utils

FIXTURES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _load_json_fixture(filename):
    with open(os.path.join(FIXTURES_PATH, filename)) as handle:
        return json.load(handle)


def _minimal_journal_data(**overrides):
    data = {
        "id": "0000-0001",
        "title": "Test Journal",
        "acronym": "tj",
        "created": "1999-07-02T00:00:00.000000Z",
        "updated": "2019-07-19T20:33:17.102106Z",
        "is_public": True,
    }
    data.update(overrides)
    return data


def _minimal_issue_data(journal_id, issue_id="0000-0001-2020-v1-n1", **overrides):
    data = {
        "id": issue_id,
        "publication_year": "2020",
        "volume": "1",
        "number": "1",
        "publication_months": {"range": [1, 3]},
        "pid": "0000000120200001",
        "created": "2020-01-01T00:00:00.000000Z",
        "updated": "2020-01-02T00:00:00.000000Z",
    }
    data.update(overrides)
    return data


def _full_article_data(**overrides):
    data = {
        "title": "Sample Article",
        "section": "Original Article",
        "abstract": "Sample abstract",
        "lang": "en",
        "doi": "10.1000/sample",
        "scielo_pids_v2": "S0000-00012020000100001",
        "aop_pid": "S0000-0001(20)00001",
        "other_pids": ["pid-one", "pid-two", "pid-one"],
        "authors_meta": [
            {"name": "Silva, João", "affiliation": "University A", "orcid": "0000-0001-2345-6789"},
            {"name": "Santos, Maria", "affiliation": "University B", "orcid": "0000-0002-2345-6789"},
        ],
        "htmls": [{"lang": "en", "uri": "https://example.com/article.html"}],
        "pdfs": [
            {
                "lang": "en",
                "url": "https://example.com/article.pdf",
                "filename": "article.pdf",
                "type": "pdf",
                "classic_uri": "https://example.com/classic.pdf",
            }
        ],
        "translated_titles": [{"language": "pt", "name": "Artigo de Exemplo"}],
        "translated_sections": [{"language": "pt", "name": "Artigo Original"}],
        "abstracts": [{"language": "pt", "text": "Resumo em português"}],
        "keywords": [{"language": "en", "keywords": ["keyword one", "keyword two"]}],
        "publication_date": "2020",
        "type": "research-article",
        "order": 1,
        "fpage": "10",
        "fpage_sequence": "a",
        "lpage": "20",
        "elocation": "e100",
        "mat_suppl_items": [
            {
                "lang": "en",
                "url": "https://example.com/suppl.pdf",
                "ref_id": "sup1",
                "filename": "suppl.pdf",
            }
        ],
        "xml": "https://example.com/article.xml",
        "doi_with_lang": [{"language": "en", "doi": "10.1000/sample-en"}],
        "related_articles": [
            {
                "doi": "10.1000/related",
                "ref_id": "B1",
                "related_type": "companion",
                "href": "https://example.com/related",
            }
        ],
        "collab": [{"name": "Consortium Alpha"}],
        "created": "2020-01-01T00:00:00.000000Z",
        "updated": "2020-01-02T00:00:00.000000Z",
        "is_public": True,
    }
    data.update(overrides)
    return data


class FactoryHelpersTestCase(BaseTestCase):
    def test_isoformat_to_datetime_with_value(self):
        result = isoformat_to_datetime("2020-01-01T00:00:00.000000Z")
        self.assertEqual(result, isoformat_to_datetime("2020-01-01T00:00:00.000000Z"))

    def test_isoformat_to_datetime_without_value(self):
        result = isoformat_to_datetime(None)
        self.assertIsInstance(result, str)
        self.assertTrue(result)

    def test_format_author_name_without_suffix(self):
        self.assertEqual(_format_author_name("Silva", "João", None), "Silva, João")

    def test_format_author_name_with_suffix(self):
        self.assertEqual(_format_author_name("Silva", "João", "Jr"), "Silva Jr, João")


class JournalFactoryTestCase(BaseTestCase):
    def test_journal_factory_creates_new_journal(self):
        with current_app.app_context():
            data = _load_json_fixture("journal_payload.json")
            journal = JournalFactory(data)
            journal.save()

            self.assertEqual(journal._id, "1678-4464")
            self.assertEqual(journal.title, "Cadernos de Saúde Pública")
            self.assertEqual(journal.editor_email, "cadernos@ensp.fiocruz.br")
            self.assertEqual(len(journal.sponsors), 1)

    def test_journal_factory_updates_existing_journal(self):
        with current_app.app_context():
            existing = utils.makeOneJournal(
                {
                    "_id": "0000-0002",
                    "logo_url": "http://example.com/missing-logo.png",
                }
            )
            data = _minimal_journal_data(
                id="0000-0002",
                logo_url="http://example.com/new-logo.png",
                issue_count=5,
            )
            journal = JournalFactory(data)

            self.assertEqual(journal._id, existing._id)
            self.assertEqual(journal.logo_url, "http://example.com/new-logo.png")
            self.assertEqual(journal.issue_count, 5)

    def test_journal_factory_sets_institutions_and_journal_links(self):
        with current_app.app_context():
            data = _minimal_journal_data(
                institution_responsible_for=[
                    {"name": "Publisher One", "city": "Rio", "state": "RJ", "country": "BR"},
                    {"name": "Publisher Two", "city": "SP", "state": "SP", "country": "BR"},
                    {"city": "Ignored"},
                ],
                next_journal={"name": "Next Journal Title"},
                previous_journal={"name": "Previous Journal Title"},
                contact={
                    "email": "one@example.com;two@example.com",
                    "address": "Street 1",
                },
                items=[{"id": "issue-1"}, {"id": "issue-2"}],
            )
            journal = JournalFactory(data)

            self.assertEqual(journal.publisher_name, "Publisher One, Publisher Two")
            self.assertEqual(journal.publisher_city, "Rio")
            self.assertEqual(journal.publisher_state, "RJ")
            self.assertEqual(journal.publisher_country, "BR")
            self.assertEqual(journal.next_title, "Next Journal Title")
            self.assertEqual(journal.previous_journal_ref, "Previous Journal Title")
            self.assertEqual(journal.editor_email, "one@example.com")
            self.assertEqual(journal.issue_count, 2)

    def test_journal_factory_without_created_uses_current_timestamp(self):
        with current_app.app_context():
            data = _minimal_journal_data()
            del data["created"]
            journal = JournalFactory(data)
            self.assertIsInstance(journal.created, str)

    def test_journal_factory_skips_institutions_without_names(self):
        with current_app.app_context():
            data = _minimal_journal_data(
                institution_responsible_for=[{"city": "Ignored"}],
            )
            journal = JournalFactory(data)
            self.assertFalse(journal.publisher_name)

    def test_journal_factory_keeps_existing_logo_when_not_missing(self):
        with current_app.app_context():
            utils.makeOneJournal(
                {
                    "_id": "0000-0006",
                    "logo_url": "http://example.com/valid-logo.png",
                }
            )
            data = _minimal_journal_data(
                id="0000-0006",
                logo_url="http://example.com/new-logo.png",
            )
            journal = JournalFactory(data)
            self.assertEqual(journal.logo_url, "http://example.com/valid-logo.png")


class IssueFactoryTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        with current_app.app_context():
            self.journal = utils.makeOneJournal({"_id": "0000-0003"})

    def test_issue_factory_creates_regular_issue(self):
        with current_app.app_context():
            data = _minimal_issue_data(self.journal._id)
            issue = IssueFactory(data, self.journal._id)
            issue.save()

            self.assertEqual(issue._id, data["id"])
            self.assertEqual(issue.year, "2020")
            self.assertEqual(issue.number, "1")
            self.assertEqual(issue.start_month, 1)
            self.assertEqual(issue.end_month, 3)
            self.assertEqual(issue.label, "v1n1")

    def test_issue_factory_updates_existing_issue_and_reuses_journal(self):
        with current_app.app_context():
            data = _minimal_issue_data(self.journal._id, issue_id="0000-0003-existing")
            first = IssueFactory(data, self.journal._id)
            first.save()

            data["publication_year"] = "2021"
            issue, _ = _get_issue_for_upsert(data)
            updated = IssueFactory(data, journal_id=None, issue=issue)

            self.assertEqual(updated._id, first._id)
            self.assertEqual(updated.journal._id, self.journal._id)
            self.assertEqual(updated.year, "2021")

    def test_issue_factory_ahead_type_sets_defaults(self):
        with current_app.app_context():
            data = _minimal_issue_data(
                self.journal._id,
                issue_id="0000-0003-aop",
                number=None,
            )
            issue = IssueFactory(data, self.journal._id)

            self.assertEqual(issue.year, "9999")
            self.assertEqual(issue.number, "ahead")

    def test_issue_factory_invalid_issue_order_is_ignored(self):
        with current_app.app_context():
            data = _minimal_issue_data(self.journal._id)
            issue = IssueFactory(data, self.journal._id, issue_order="not-a-number")
            self.assertIsNone(issue.order)

    def test_issue_factory_infers_type_supplement(self):
        with current_app.app_context():
            data = _minimal_issue_data(
                self.journal._id,
                issue_id="0000-0003-suppl",
                supplement="Supplement text",
                number=None,
            )
            issue = IssueFactory(data, self.journal._id)
            self.assertEqual(issue.type, "supplement")

    def test_issue_factory_infers_type_volume_issue(self):
        with current_app.app_context():
            data = _minimal_issue_data(
                self.journal._id,
                issue_id="0000-0003-vol",
                volume="10",
                number=None,
            )
            issue = IssueFactory(data, self.journal._id)
            self.assertEqual(issue.type, "volume_issue")

    def test_issue_factory_infers_type_special(self):
        with current_app.app_context():
            data = _minimal_issue_data(
                self.journal._id,
                issue_id="0000-0003-spe",
                number="spe1",
            )
            issue = IssueFactory(data, self.journal._id)
            self.assertEqual(issue.type, "special")

    def test_issue_factory_infers_type_outdated_ahead(self):
        with current_app.app_context():
            data = _minimal_issue_data(
                self.journal._id,
                issue_id="0000-0003-aop",
            )
            issue = IssueFactory(data, self.journal._id)
            self.assertEqual(issue.type, "outdated_ahead")

    def test_issue_factory_uses_pid_suffix_for_order(self):
        with current_app.app_context():
            data = _minimal_issue_data(
                self.journal._id,
                issue_id="0000-0003-order",
                pid="12345678901234",
            )
            issue = IssueFactory(data, self.journal._id, issue_order=None)
            self.assertEqual(issue.order, 1234)

    def test_issue_factory_keeps_explicit_type(self):
        with current_app.app_context():
            data = _minimal_issue_data(
                self.journal._id,
                issue_id="0000-0003-explicit-type",
                type="press_release",
                supplement="ignored",
            )
            issue = IssueFactory(data, self.journal._id)
            self.assertEqual(issue.type, "press_release")

    def test_issue_factory_defaults_to_passed_type(self):
        with current_app.app_context():
            data = _minimal_issue_data(
                self.journal._id,
                issue_id="0000-0003-regular-type",
                items=[{"id": "article-1"}],
            )
            issue = IssueFactory(
                data,
                self.journal._id,
                _type="special",
            )
            self.assertEqual(issue.type, "special")

    def test_get_issue_for_upsert_finds_by_pid_when_id_changes(self):
        with current_app.app_context():
            data = _minimal_issue_data(
                self.journal._id,
                issue_id="0000-0003-2020-v1-n1",
                pid="0000000320200002",
            )
            original = IssueFactory(data, self.journal._id)
            original.save()

            data["id"] = "0000-0003-2020-v1"
            data["number"] = None
            issue, old_ids = _get_issue_for_upsert(data)

            self.assertEqual(old_ids, ["0000-0003-2020-v1-n1"])
            self.assertEqual(issue._id, original._id)
            self.assertEqual(issue.journal._id, self.journal._id)
            self.assertEqual(issue.is_public, original.is_public)

    def test_get_issue_for_upsert_prefers_document_with_target_id(self):
        with current_app.app_context():
            pid = "0000000320200003"
            utils.makeOneIssue(
                {
                    "_id": "0000-0003-2020-v1-n1",
                    "journal": self.journal,
                    "pid": pid,
                    "number": "1",
                }
            )
            utils.makeOneIssue(
                {
                    "_id": "0000-0003-2020-v1",
                    "journal": self.journal,
                    "pid": pid,
                    "number": None,
                }
            )

            issue, old_ids = _get_issue_for_upsert(
                _minimal_issue_data(
                    self.journal._id,
                    issue_id="0000-0003-2020-v1",
                    pid=pid,
                    number=None,
                )
            )

            self.assertEqual(issue._id, "0000-0003-2020-v1")
            self.assertEqual(old_ids, ["0000-0003-2020-v1-n1"])

    def test_get_issue_for_upsert_does_not_lookup_by_id_without_pid(self):
        with current_app.app_context():
            data = _minimal_issue_data(
                self.journal._id,
                issue_id="0000-0003-no-pid",
            )
            data.pop("pid")
            saved = IssueFactory(data, self.journal._id)
            saved.save()

            issue, old_ids = _get_issue_for_upsert(data)

            self.assertIsNone(issue.pk)
            self.assertEqual(old_ids, [])

    def test_issue_factory_updates_existing_issue_when_id_changes_same_pid(self):
        with current_app.app_context():
            data = _minimal_issue_data(
                self.journal._id,
                issue_id="0000-0003-2020-v1-n1",
                pid="0000000320200004",
            )
            first = IssueFactory(data, self.journal._id)
            first.save()

            data["id"] = "0000-0003-2020-v1"
            data["number"] = None
            issue, _ = _get_issue_for_upsert(data)
            updated = IssueFactory(data, journal_id=None, issue=issue)

            self.assertEqual(updated._id, "0000-0003-2020-v1")
            self.assertEqual(updated.iid, "0000-0003-2020-v1")
            self.assertEqual(updated.pid, "0000000320200004")
            self.assertEqual(updated.journal._id, self.journal._id)
            self.assertIsNone(updated.number)
            self.assertEqual(updated.label, "v1")


class AuxiliarArticleFactoryTestCase(BaseTestCase):
    def _make_issue(self, issue_id="0000-0004-issue", number="1", **issue_attrs):
        journal = utils.makeOneJournal({"_id": "0000-0004"})
        issue_attrs.setdefault("journal", journal)
        issue_attrs.setdefault("_id", issue_id)
        issue_attrs.setdefault("number", number)
        return journal, utils.makeOneIssue(issue_attrs)

    def test_auxiliar_factory_creates_new_document(self):
        with current_app.app_context():
            journal, issue = self._make_issue()
            factory = AuxiliarArticleFactory("doc-new", issue._id)
            self.assertEqual(factory.doc._id, "doc-new")
            self.assertEqual(factory.doc.issue._id, issue._id)
            self.assertEqual(factory.doc.journal._id, journal._id)

    def test_auxiliar_factory_skips_issue_lookup_when_document_has_issue(self):
        with current_app.app_context():
            journal, issue = self._make_issue(issue_id="0000-0004-with-issue")
            existing = utils.makeOneArticle(
                {
                    "_id": "doc-with-issue",
                    "issue": issue,
                    "journal": journal,
                }
            )
            factory = AuxiliarArticleFactory("doc-with-issue", "missing-issue-id")
            self.assertEqual(factory.doc.issue._id, existing.issue._id)

    def test_auxiliar_factory_loads_existing_document(self):
        with current_app.app_context():
            journal, issue = self._make_issue(issue_id="0000-0004-existing")
            existing = utils.makeOneArticle(
                {
                    "_id": "doc-existing",
                    "issue": issue,
                    "journal": journal,
                    "title": "Existing title",
                }
            )
            factory = AuxiliarArticleFactory("doc-existing", issue._id)
            self.assertEqual(factory.doc.title, existing.title)

    def test_add_identifiers_and_other_pids(self):
        with current_app.app_context():
            _, issue = self._make_issue(issue_id="0000-0004-identifiers")
            factory = AuxiliarArticleFactory("doc-identifiers", issue._id)
            factory.add_identifiers(
                v2="v2-pid",
                aop_pid="aop-pid",
                other_pids=["other-1", "other-1", None, "other-2"],
            )

            self.assertEqual(factory.doc.pid, "v2-pid")
            self.assertEqual(factory.doc.aop_pid, "aop-pid")
            self.assertEqual(factory.doc.scielo_pids["other"], ["other-1", "other-2"])

    def test_add_other_pid_ignores_falsy_values(self):
        with current_app.app_context():
            _, issue = self._make_issue(issue_id="0000-0004-other-pid")
            factory = AuxiliarArticleFactory("doc-other-pid", issue._id)
            factory.doc.scielo_pids = {"v2": "pid", "v3": "doc-other-pid"}
            factory.add_other_pid(None)
            factory.add_other_pid("")
            self.assertNotIn("other", factory.doc.scielo_pids)

    def test_add_journal_and_issue_accepts_objects_and_ids(self):
        with current_app.app_context():
            _, issue = self._make_issue(issue_id="0000-0004-base")
            other_journal = utils.makeOneJournal({"_id": "0000-0004-other-j"})
            other_issue = utils.makeOneIssue(
                {"_id": "0000-0004-other-i", "journal": other_journal}
            )

            factory = AuxiliarArticleFactory("doc-journal-issue", issue._id)
            factory.add_journal(other_journal)
            factory.add_issue(other_issue)
            self.assertEqual(factory.doc.journal._id, other_journal._id)
            self.assertEqual(factory.doc.issue._id, other_issue._id)

            factory.add_journal(other_journal._id)
            factory.add_issue(other_issue._id)
            self.assertEqual(factory.doc.journal._id, other_journal._id)
            self.assertEqual(factory.doc.issue._id, other_issue._id)

    def test_add_embedded_metadata_methods(self):
        with current_app.app_context():
            _, issue = self._make_issue(issue_id="0000-0004-metadata")
            factory = AuxiliarArticleFactory("doc-metadata", issue._id)
            factory.add_main_metadata("Title", "Section", "Abstract", "en", "10.1/test")
            factory.add_document_type("research-article")
            factory.add_publication_date("2020")
            factory.add_in_issue(1, fpage="1", fpage_seq="a", lpage="9", elocation="e1")
            factory.add_author("Author One", "Aff 1", "0000-0001-1111-1111")
            factory.add_author("Author Two", "Aff 2", "0000-0002-2222-2222")
            factory.add_translated_title("pt", "Título")
            factory.add_section("pt", "Seção")
            factory.add_abstract("pt", "Resumo")
            factory.add_keywords("en", ["kw1", "kw2"])
            factory.add_doi_with_lang("en", "10.1/test-en")
            factory.add_related_article("10.1/rel", "R1", "companion", "https://rel")
            factory.add_xml("https://example.com/article.xml")
            factory.add_html("en", "https://example.com/article.html")
            factory.add_html("pt", "https://example.com/article-pt.html")
            factory.add_pdf("en", "https://pdf", "file.pdf", "pdf", classic_uri="https://classic")
            factory.add_mat_suppl("en", "https://suppl", "s1", "suppl.pdf")
            factory.add_collab("Consortium Beta")

            doc = factory.doc
            self.assertEqual(doc.title, "Title")
            self.assertEqual(len(doc.authors_meta), 2)
            self.assertEqual(len(doc.authors), 2)
            self.assertEqual(len(doc.translated_titles), 1)
            self.assertEqual(len(doc.sections), 1)
            self.assertEqual(len(doc.abstracts), 1)
            self.assertEqual(doc.abstract_languages, ["pt"])
            self.assertEqual(len(doc.keywords), 1)
            self.assertEqual(len(doc.doi_with_lang), 1)
            self.assertEqual(len(doc.related_articles), 1)
            self.assertEqual(doc.languages, ["en", "pt"])
            self.assertEqual(len(doc.pdfs), 1)
            self.assertEqual(len(doc.mat_suppl_items), 1)
            self.assertEqual(len(doc.collabs), 1)

    def test_add_methods_initialize_none_list_fields(self):
        with current_app.app_context():
            _, issue = self._make_issue(issue_id="0000-0004-none-fields")
            factory = AuxiliarArticleFactory("doc-none-fields", issue._id)
            doc = factory.doc
            for field in (
                "authors_meta",
                "authors",
                "translated_titles",
                "sections",
                "abstracts",
                "abstract_languages",
                "keywords",
                "doi_with_lang",
                "related_articles",
                "htmls",
                "pdfs",
                "mat_suppl_items",
                "collabs",
            ):
                doc._data[field] = None

            factory.add_author("Author", "Aff", "0000-0001-1111-1111")
            doc._data["authors"] = None
            factory.add_author("Second Author", "Aff 2", "0000-0002-2222-2222")
            factory.add_translated_title("pt", "Título")
            factory.add_section("pt", "Seção")
            factory.add_abstract("pt", "Resumo")
            factory.add_keywords("en", ["kw"])
            factory.add_doi_with_lang("en", "10.1/test")
            factory.add_related_article("10.1/rel", "R1", "companion", "https://rel")
            factory.add_html("en", "https://example.com/article.html")
            factory.add_pdf("en", "https://pdf", "file.pdf", "pdf")
            factory.add_mat_suppl("en", "https://suppl", "s1", "suppl.pdf")
            factory.add_collab("Consortium")

            self.assertEqual(len(doc.authors_meta), 2)
            self.assertEqual(len(doc.authors), 1)
            self.assertEqual(len(doc.translated_titles), 1)
            self.assertEqual(len(doc.sections), 1)
            self.assertEqual(len(doc.abstracts), 1)
            self.assertEqual(doc.abstract_languages, ["pt"])
            self.assertEqual(len(doc.keywords), 1)
            self.assertEqual(len(doc.doi_with_lang), 1)
            self.assertEqual(len(doc.related_articles), 1)
            self.assertEqual(len(doc.htmls), 1)
            self.assertEqual(len(doc.pdfs), 1)
            self.assertEqual(len(doc.mat_suppl_items), 1)
            self.assertEqual(len(doc.collabs), 1)

    def test_add_mat_suppl_appends_to_existing_list(self):
        with current_app.app_context():
            _, issue = self._make_issue(issue_id="0000-0004-matsuppl")
            factory = AuxiliarArticleFactory("doc-matsuppl", issue._id)
            factory.doc.mat_suppl_items = []
            factory.add_mat_suppl("en", "https://suppl-1", "s1", "one.pdf")
            factory.add_mat_suppl("pt", "https://suppl-2", "s2", "two.pdf")
            self.assertEqual(len(factory.doc.mat_suppl_items), 2)

    def test_publish_document_sets_aop_url_segments_for_ahead_issue(self):
        with current_app.app_context():
            journal, ahead_issue = self._make_issue(
                issue_id="0000-0004-ahead",
                number="ahead",
                url_segment="ahead-seg",
            )
            factory = AuxiliarArticleFactory("doc-ahead", ahead_issue._id)
            factory.doc.url_segment = "article-seg"
            factory.doc.title = "Ahead article"
            factory.doc.original_language = "en"
            factory.doc.publication_date = "2020"
            expected_issue_seg = factory.doc.issue.url_segment
            factory.publish_document(
                "2020-01-01T00:00:00.000000Z",
                "2020-01-02T00:00:00.000000Z",
                True,
            )

            saved = models.Article.objects.get(_id="doc-ahead")
            self.assertIsNotNone(saved.aop_url_segs)
            self.assertEqual(saved.aop_url_segs.url_seg_article, "article-seg")
            self.assertEqual(saved.aop_url_segs.url_seg_issue, expected_issue_seg)

    def test_publish_document_syncs_issue_visibility(self):
        with current_app.app_context():
            journal, private_issue = self._make_issue(
                issue_id="0000-0004-private",
                is_public=False,
            )
            factory = AuxiliarArticleFactory("doc-public", private_issue._id)
            factory.doc.title = "Public article"
            factory.doc.original_language = "en"
            factory.doc.publication_date = "2020"
            factory.publish_document(
                "2020-01-01T00:00:00.000000Z",
                "2020-01-02T00:00:00.000000Z",
                True,
            )

            private_issue.reload()
            self.assertTrue(private_issue.is_public)

    def test_publish_document_unpublishes_issue_without_public_articles(self):
        with current_app.app_context():
            journal, public_issue = self._make_issue(
                issue_id="0000-0004-public",
                is_public=True,
            )
            factory = AuxiliarArticleFactory("doc-private", public_issue._id)
            factory.doc.title = "Private article"
            factory.doc.original_language = "en"
            factory.doc.publication_date = "2020"
            factory.publish_document(
                "2020-01-01T00:00:00.000000Z",
                "2020-01-02T00:00:00.000000Z",
                False,
            )

            public_issue.reload()
            self.assertFalse(public_issue.is_public)

    def test_publish_document_raises_publish_document_error(self):
        with current_app.app_context():
            _, issue = self._make_issue(issue_id="0000-0004-error")
            factory = AuxiliarArticleFactory("doc-error", issue._id)
            factory.doc.title = "Broken article"
            factory.doc.original_language = "en"
            factory.doc.publication_date = "2020"

            with patch.object(models.Article, "save", side_effect=RuntimeError("save failed")):
                with self.assertRaises(PublishDocumentError):
                    factory.publish_document(
                        "2020-01-01T00:00:00.000000Z",
                        "2020-01-02T00:00:00.000000Z",
                        True,
                    )


class ArticleFactoryTestCase(BaseTestCase):
    def _make_issue(self):
        journal = utils.makeOneJournal({"_id": "0000-0005"})
        issue = utils.makeOneIssue(
            {
                "_id": "0000-0005-issue",
                "journal": journal,
            }
        )
        return issue

    def test_article_factory_builds_full_article(self):
        with current_app.app_context():
            issue = self._make_issue()
            data = _full_article_data()
            article = ArticleFactory(
                "article-full",
                data,
                issue._id,
                document_order=1,
                document_xml_url="https://example.com/article.xml",
            )

            saved = models.Article.objects.get(_id="article-full")
            self.assertEqual(saved.title, "Sample Article")
            self.assertEqual(saved.pid, "S0000-00012020000100001")
            self.assertEqual(len(saved.authors_meta), 2)
            self.assertEqual(len(saved.htmls), 1)
            self.assertEqual(len(saved.pdfs), 1)
            self.assertEqual(len(saved.translated_titles), 1)
            self.assertEqual(len(saved.sections), 1)
            self.assertEqual(len(saved.abstracts), 1)
            self.assertEqual(len(saved.keywords), 1)
            self.assertEqual(len(saved.mat_suppl), 0)
            self.assertEqual(len(article.mat_suppl_items), 1)
            self.assertEqual(len(saved.doi_with_lang), 1)
            self.assertEqual(len(saved.related_articles), 1)
            self.assertEqual(len(saved.collabs), 0)
            self.assertEqual(len(article.collabs), 1)
            self.assertEqual(article._id, saved._id)

    def test_article_factory_with_minimal_data(self):
        with current_app.app_context():
            issue = self._make_issue()
            article = ArticleFactory(
                "article-minimal",
                {
                    "created": "2020-01-01T00:00:00.000000Z",
                    "updated": "2020-01-02T00:00:00.000000Z",
                    "is_public": False,
                },
                issue._id,
                document_order=1,
                document_xml_url="https://example.com/minimal.xml",
            )

            saved = models.Article.objects.get(_id="article-minimal")
            self.assertEqual(saved._id, article._id)
            self.assertFalse(saved.is_public)
