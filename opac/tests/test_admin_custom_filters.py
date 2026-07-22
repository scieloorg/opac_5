# coding: utf-8
import unittest
from uuid import uuid4

from flask_admin.contrib.mongoengine.tools import parse_like_term
from flask_babel import lazy_gettext as __
from mongoengine.queryset import Q
from opac_schema.v1.models import Article, Issue, Journal, Pages
from tests.utils import makeOneArticle, makeOneIssue, makeOneJournal, makeOnePage
from webapp.admin.custom_filters import (
    CustomFilterConverter,
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

    def test_flt_string_column_name(self):
        """Flask-Admin 2.2 may pass column as str (reproduces /admin/pages/ crash)."""
        op, term = parse_like_term("page-%s" % str(uuid4().hex))

        result = get_flt("name", term, op)

        expected = Q(**{"name__%s" % op: term})
        self.assertEqual(expected.query, result.query)

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

    def test_filters_string_field_keeps_field_object(self):
        filter_converter = CustomFilterConverter()
        result = filter_converter.convert("StringField", Pages.name, "Nome")

        self.assertTrue(result)
        self.assertTrue(all(i.column is Pages.name for i in result))
        self.assertIn(CustomFilterLike, [type(i) for i in result])

    def test_custom_filter_like_with_string_column(self):
        page_name = "page-%s" % str(uuid4().hex)
        makeOnePage({"name": page_name})
        custom_filter = CustomFilterLike(column="name", name=__("Nome"))

        result = custom_filter.apply(Pages.objects, page_name)

        term, data = parse_like_term(page_name)
        expected = Pages.objects.filter(Q(**{"name__%s" % term: data}))

        self.assertListEqual([_ for _ in expected], [_ for _ in result])

    def test_custom_filter_like_via_converter_on_pages(self):
        """End-to-end path used by PagesAdminView column_filters."""
        page_name = "page-%s" % str(uuid4().hex)
        makeOnePage({"name": page_name})

        filters = CustomFilterConverter().convert("StringField", Pages.name, "Nome")
        like_filter = next(f for f in filters if isinstance(f, CustomFilterLike))

        result = like_filter.apply(Pages.objects, page_name)

        term, data = parse_like_term(page_name)
        expected = Pages.objects.filter(Q(**{"name__%s" % term: data}))
        self.assertListEqual([_ for _ in expected], [_ for _ in result])

    def test_custom_filter_equal_with_string_column(self):
        page_name = "page-%s" % str(uuid4().hex)
        makeOnePage({"name": page_name})
        custom_filter = CustomFilterEqual(column="name", name=__("Nome"))

        result = custom_filter.apply(Pages.objects, page_name)
        expected = Pages.objects.filter(Q(name=page_name))

        self.assertListEqual([_ for _ in expected], [_ for _ in result])

    def test_custom_filter_empty_with_string_column(self):
        makeOnePage({"name": "filled-%s" % str(uuid4().hex)})
        custom_filter = CustomFilterEmpty(column="description", name=__("Descrição"))

        result = custom_filter.apply(Pages.objects, "1")
        expected = Pages.objects.filter(Q(description=None))

        self.assertListEqual([_ for _ in expected], [_ for _ in result])

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

    @unittest.skip("Pula essa teste temporariamente...")
    def test_custom_filter_not_like(self):
        journal = makeOneJournal({"title": "title-%s" % str(uuid4().hex)})
        makeOneIssue({"journal": journal})
        column = Issue.journal
        custom_filter = CustomFilterNotLike(column=column, name=__("Periódico"))

        result = custom_filter.apply(Issue.objects, journal.title)

        term, data = parse_like_term(journal.title)
        journals = Journal.objects.filter(Q(**{"title__not__%s" % term: data}))
        expected = Issue.objects.filter(Q(**{"%s__in" % column.name: journals}))

        self.assertListEqual([_ for _ in expected], [_ for _ in result])

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
