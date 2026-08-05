# coding: utf-8
import unittest
from uuid import uuid4

from flask_admin.contrib.mongoengine.tools import parse_like_term
from flask_babel import lazy_gettext as __
from mongoengine import Document, EmbeddedDocument, EmbeddedDocumentField, StringField
from mongoengine.queryset import Q
from opac_schema.v1.models import Article, Issue, Journal, News, Sponsor
from tests.utils import makeOneArticle, makeOneIssue, makeOneJournal
from webapp import models
from webapp.admin.custom_filters import (
    CustomFilterConverter,
    CustomFilterConverterSqla,
    CustomFilterEmpty,
    CustomFilterEqual,
    CustomFilterInList,
    CustomFilterLike,
    CustomFilterNotEqual,
    CustomFilterNotInList,
    CustomFilterNotLike,
    _column_name,
    get_flt,
)

from .base import BaseTestCase


class _LicenseInfo(EmbeddedDocument):
    license_code = StringField()
    reference_url = StringField()
    disclaimer = StringField()


class _UseLicensesDoc(Document):
    meta = {"collection": "test_use_licenses_coverage"}
    title = StringField()
    use_licenses = EmbeddedDocumentField(_LicenseInfo)


class CustomFiltersTestCase(BaseTestCase):
    def test_column_name_accepts_field_and_str(self):
        self.assertEqual(_column_name(Pages.name), "name")
        self.assertEqual(_column_name("name"), "name")

    def test_flt_reference_journal(self):
        journal_fields = {
            "title": "title-%s" % str(uuid4().hex),
            "title_iso": "title_iso-%s" % str(uuid4().hex),
            "short_title": "short_title-%s" % str(uuid4().hex),
            "acronym": "acronym-%s" % str(uuid4().hex),
            "print_issn": "print_issn-%s" % str(uuid4().hex),
            "eletronic_issn": "eletronic_issn-%s" % str(uuid4().hex),
        }

        journal = makeOneJournal(journal_fields)
        makeOneIssue({"journal": journal})

        for field in journal_fields:
            op, term = parse_like_term(journal[field])
            result = get_flt(Issue.journal, term, op)

            journals = Journal.objects.filter(Q(**{"%s__%s" % (field, op): term}))
            expected = Q(**{"journal__in": journals})

            self.assertIn("journal__in", result.query)

            self.assertListEqual(
                [_ for _ in expected.query["journal__in"]],
                [_ for _ in result.query["journal__in"]],
            )

    def test_flt_search_reference_issue(self):
        journal = makeOneJournal()
        issue = makeOneIssue({"journal": journal})
        makeOneArticle({"journal": journal, "issue": issue})

        op, term = parse_like_term(issue.label)
        result = get_flt(Article.issue, term, op)

        issues = Issue.objects.filter(Q(**{"label__%s" % op: term}))
        expected = Q(**{"issue__in": issues})

        self.assertIn("issue__in", result.query)
        self.assertListEqual(
            [_ for _ in expected.query["issue__in"]],
            [_ for _ in result.query["issue__in"]],
        )

    def test_flt_list_field(self):
        op, term = parse_like_term("title-%s" % str(uuid4().hex))
        result = get_flt(Journal.title, term, op)
        self.assertIsNotNone(result)

    def test_flt_string_field(self):
        op, term = parse_like_term("index-%s" % str(uuid4().hex))

        result = get_flt(Journal.index_at, term, op)

        expected = Q(**{"%s__%s" % (Journal.index_at.name, op): term})

        self.assertEqual(expected.query, result.query)

    def test_flt_reference_journal_with_ne_term(self):
        journal = makeOneJournal({"title": "ne-term-%s" % uuid4().hex})
        makeOneIssue({"journal": journal})

        result = get_flt(Issue.journal, journal.title, "ne")
        journals = Journal.objects.filter(Q(**{"title__ne": journal.title}))
        expected = Q(**{"journal__in": journals})

        self.assertListEqual(
            [_ for _ in expected.query["journal__in"]],
            [_ for _ in result.query["journal__in"]],
        )

    def test_flt_embedded_document_field(self):
        license_code = "license-%s" % uuid4().hex
        doc = _UseLicensesDoc(
            title="embedded-doc",
            use_licenses=_LicenseInfo(
                license_code=license_code,
                reference_url="https://example.com",
                disclaimer="disclaimer",
            ),
        ).save()

        result = get_flt(_UseLicensesDoc.use_licenses, license_code, "icontains")
        matched = _UseLicensesDoc.objects.filter(result)
        self.assertEqual(1, matched.count())
        self.assertEqual(doc.id, matched.first().id)
        doc.delete()

    def test_flt_embedded_document_field_with_ne_term(self):
        license_code = "embedded-ne-%s" % uuid4().hex
        other_code = "other-%s" % uuid4().hex
        doc = _UseLicensesDoc(
            title="embedded-ne-doc",
            use_licenses=_LicenseInfo(license_code=other_code),
        ).save()

        result = get_flt(_UseLicensesDoc.use_licenses, license_code, "ne")
        matched = _UseLicensesDoc.objects.filter(result)
        self.assertEqual(1, matched.count())
        doc.delete()

    def test_flt_list_field_empty_value(self):
        result = get_flt(Journal.index_at, None, "in")
        expected = Q(**{"index_at__in": []})
        self.assertEqual(expected.query, result.query)

    def test_custom_filter_equal_apply(self):
        title = "equal-filter-%s" % uuid4().hex
        journal = makeOneJournal({"title": title})
        custom_filter = CustomFilterEqual(column=Journal.title, name=__("Título"))

        result = custom_filter.apply(Journal.objects, title)
        expected = Journal.objects.filter(get_flt(Journal.title, title))

        self.assertListEqual([_ for _ in expected], [_ for _ in result])

    def test_custom_filter_empty_apply(self):
        custom_filter = CustomFilterEmpty(column=Journal.title, name=__("Título"))

        result_is_empty = custom_filter.apply(Journal.objects, "1")
        result_is_not_empty = custom_filter.apply(Journal.objects, "0")

        self.assertIsNotNone(result_is_empty)
        self.assertIsNotNone(result_is_not_empty)

    def test_filters_reference_field(self):
        filter_converter = CustomFilterConverter()
        filtes_reference_field = (
            CustomFilterLike,
            CustomFilterNotLike,
            CustomFilterEqual,
            CustomFilterNotEqual,
            CustomFilterInList,
            CustomFilterNotInList,
        )

        result = filter_converter.convert("ReferenceField", Issue.journal, "journal")
        expected = [f(Issue.journal, "journal") for f in filtes_reference_field]
        self.assertListEqual([i.name for i in expected], [i.name for i in result])
        self.assertListEqual([i.options for i in expected], [i.options for i in result])
        self.assertListEqual(
            [i.__class__.__name__ for i in expected],
            [i.__class__.__name__ for i in result],
        )
        # Field object must be preserved for ReferenceField filtering.
        self.assertTrue(all(i.column is Issue.journal for i in result))

    def test_filters_list_field(self):
        filter_converter = CustomFilterConverter()
        filtes_list_field = (CustomFilterLike, CustomFilterNotLike, CustomFilterEmpty)

        result = filter_converter.convert("ListField", Journal.index_at, "index_at")
        expected = [f(Journal.index_at, "index_at") for f in filtes_list_field]
        self.assertListEqual([i.name for i in expected], [i.name for i in result])
        self.assertListEqual([i.options for i in expected], [i.options for i in result])
        self.assertListEqual(
            [i.__class__.__name__ for i in expected],
            [i.__class__.__name__ for i in result],
        )

    def test_filters_embedded_document_field(self):
        filter_converter = CustomFilterConverter()
        embedded_filters = (
            CustomFilterLike,
            CustomFilterNotLike,
            CustomFilterEqual,
            CustomFilterNotEqual,
            CustomFilterEmpty,
            CustomFilterInList,
            CustomFilterNotInList,
        )

        result = filter_converter.convert(
            "EmbeddedDocumentField",
            _UseLicensesDoc.use_licenses,
            "use_licenses",
        )
        expected = [
            f(_UseLicensesDoc.use_licenses, "use_licenses") for f in embedded_filters
        ]
        self.assertListEqual([i.name for i in expected], [i.name for i in result])
        self.assertListEqual(
            [i.__class__.__name__ for i in expected],
            [i.__class__.__name__ for i in result],
        )

    def test_filters_string_url_and_email_fields(self):
        filter_converter = CustomFilterConverter()
        string_filters = (
            CustomFilterLike,
            CustomFilterNotLike,
            CustomFilterEqual,
            CustomFilterNotEqual,
            CustomFilterEmpty,
            CustomFilterInList,
            CustomFilterNotInList,
        )

        for column, name in (
            (Journal.title, "title"),
            (Sponsor.url, "url"),
            (News.url, "news_url"),
        ):
            result = filter_converter.conv_string(column, name)
            expected = [f(column, name) for f in string_filters]
            self.assertListEqual([i.name for i in expected], [i.name for i in result])

    def test_sqla_filter_converter_choice_with_and_without_options(self):
        converter = CustomFilterConverterSqla()

        result_default = converter.conv_choice(models.File.language, "language", None)
        self.assertEqual(5, len(result_default))
        self.assertEqual("language", result_default[0].name)
        self.assertEqual(models.LANGUAGES_CHOICES, result_default[0].options)

        custom_options = [("fr", "French")]
        result_custom = converter.conv_choice(
            models.File.language, "language", custom_options
        )
        self.assertEqual(custom_options, result_custom[0].options)

    def test_custom_filter_not_equal(self):
        journal = makeOneJournal({"title": "title-%s" % str(uuid4().hex)})
        makeOneIssue({"journal": journal})
        column = Issue.journal
        custom_filter = CustomFilterNotEqual(column=column, name=__("Periódico"))

        result = custom_filter.apply(Issue.objects, journal.title)

        journals = Journal.objects.filter(Q(**{"title__ne": journal.title}))
        expected = Issue.objects.filter(Q(**{"%s__in" % column.name: journals}))

        self.assertListEqual([_ for _ in expected], [_ for _ in result])

    def test_custom_filter_like(self):
        journal = makeOneJournal({"title": "title-%s" % str(uuid4().hex)})
        makeOneIssue({"journal": journal})
        column = Issue.journal
        custom_filter = CustomFilterLike(column=column, name=__("Periódico"))

        result = custom_filter.apply(Issue.objects, journal.title)

        term, data = parse_like_term(journal.title)
        journals = Journal.objects.filter(Q(**{"title__%s" % term: data}))
        expected = Issue.objects.filter(Q(**{"%s__in" % column.name: journals}))

        self.assertListEqual([_ for _ in expected], [_ for _ in result])

    def test_custom_filter_not_like(self):
        journal = makeOneJournal({"title": "title-%s" % str(uuid4().hex)})
        makeOneIssue({"journal": journal})
        column = Issue.journal
        custom_filter = CustomFilterNotLike(column=column, name=__("Periódico"))

        result = custom_filter.apply(Issue.objects, journal.title)

        self.assertIsNotNone(result)
        list(result)

    def test_custom_filter_in_list(self):
        journal = makeOneJournal({"title": "title-%s" % str(uuid4().hex)})
        makeOneIssue({"journal": journal})
        column = Issue.journal
        custom_filter = CustomFilterInList(column=column, name=__("Periódico"))

        result = custom_filter.apply(Issue.objects, [journal.title])

        journals = Journal.objects.filter(Q(**{"title__in": [journal.title]}))
        expected = Issue.objects.filter(Q(**{"%s__in" % column.name: journals}))

        self.assertListEqual([_ for _ in expected], [_ for _ in result])

    def test_custom_filter_not_in_list(self):
        journal = makeOneJournal({"title": "title-%s" % str(uuid4().hex)})
        makeOneIssue({"journal": journal})
        column = Issue.journal
        custom_filter = CustomFilterNotInList(column=column, name=__("Periódico"))

        result = custom_filter.apply(Issue.objects, [journal.title])

        journals = Journal.objects.filter(Q(**{"title__nin": [journal.title]}))
        expected = Issue.objects.filter(Q(**{"%s__in" % column.name: journals}))

        self.assertListEqual([_ for _ in expected], [_ for _ in result])
