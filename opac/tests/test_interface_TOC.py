# coding: utf-8

from flask import url_for

from . import utils
from .base import BaseTestCase


class TOCTestCase(BaseTestCase):
    # TOC
    def test_the_title_of_the_article_list_when_language_pt(self):
        """
        Teste para verificar se a interface do TOC esta retornando o título no
        idioma Português.
        """
        journal = utils.makeOneJournal()

        with self.client as c:
            # Criando uma coleção para termos o objeto ``g`` na interface
            utils.makeOneCollection()

            issue = utils.makeOneIssue({"journal": journal})

            translated_titles = [
                {"name": "Artigo Com Título Em Português", "language": "pt"},
                {"name": "Título Del Artículo En Portugués", "language": "es"},
                {"name": "Article Title In Portuguese", "language": "en"},
            ]

            utils.makeOneArticle(
                {
                    "issue": issue,
                    "title": "Article Y",
                    "translated_titles": translated_titles,
                }
            )

            # Acessa o TOC diretamente com idioma pt na URL (pull_lang define session["lang"] = pt_BR)
            toc_url_pt = url_for(
                "main.issue_toc",
                url_seg=journal.url_segment,
                url_seg_issue=issue.url_segment,
                lang="pt",
            )
            response = c.get(toc_url_pt)

            self.assertEqual(200, response.status_code)
            self.assertIn(b'lang="pt', response.data)
            self.assertIn(
                "Artigo Com Título Em Português", response.data.decode("utf-8")
            )

    def test_the_title_of_the_article_list_when_language_es(self):
        """
        Teste para verificar se a interface do TOC esta retornando o título no
        idioma Espanhol.
        """
        journal = utils.makeOneJournal()

        with self.client as c:
            # Criando uma coleção para termos o objeto ``g`` na interface
            utils.makeOneCollection()

            issue = utils.makeOneIssue({"journal": journal})

            translated_titles = [
                {"name": "Artigo Com Título Em Português", "language": "pt"},
                {"name": "Título Del Artículo En Portugués", "language": "es"},
                {"name": "Article Title In Portuguese", "language": "en"},
            ]

            utils.makeOneArticle(
                {
                    "issue": issue,
                    "title": "Article Y",
                    "translated_titles": translated_titles,
                }
            )

            # Acessa o TOC diretamente com idioma es na URL (pull_lang define session["lang"])
            toc_url_es = url_for(
                "main.issue_toc",
                url_seg=journal.url_segment,
                url_seg_issue=issue.url_segment,
                lang="es",
            )
            response = c.get(toc_url_es)

            self.assertEqual(200, response.status_code)
            self.assertIn(b'lang="es"', response.data)
            self.assertIn(
                "Título Del Artículo En Portugués", response.data.decode("utf-8")
            )

    def test_the_title_of_the_article_list_when_language_en(self):
        """
        Teste para verificar se a interface do TOC esta retornando o título no
        idioma Inglês.
        """
        journal = utils.makeOneJournal()

        with self.client as c:
            # Criando uma coleção para termos o objeto ``g`` na interface
            utils.makeOneCollection()

            issue = utils.makeOneIssue({"journal": journal})

            translated_titles = [
                {"name": "Artigo Com Título Em Português", "language": "pt"},
                {"name": "Título Del Artículo En Portugués", "language": "es"},
                {"name": "Article Title In Portuguese", "language": "en"},
            ]

            utils.makeOneArticle(
                {
                    "issue": issue,
                    "title": "Article Y",
                    "translated_titles": translated_titles,
                }
            )

            # Acessa o TOC diretamente com idioma en na URL (pull_lang define session["lang"])
            toc_url_en = url_for(
                "main.issue_toc",
                url_seg=journal.url_segment,
                url_seg_issue=issue.url_segment,
                lang="en",
            )
            response = c.get(toc_url_en)

            self.assertEqual(200, response.status_code)
            self.assertIn(b'lang="en"', response.data)
            self.assertIn("Article Title In Portuguese", response.data.decode("utf-8"))

    def test_the_title_of_the_article_list_without_translated(self):
        """
        Teste para verificar se a interface do TOC esta retornando o título no
        idioma original quando não tem idioma.
        """
        journal = utils.makeOneJournal()

        with self.client as c:
            # Criando uma coleção para termos o objeto ``g`` na interface
            utils.makeOneCollection()

            issue = utils.makeOneIssue({"journal": journal})

            translated_titles = []

            utils.makeOneArticle(
                {
                    "issue": issue,
                    "title": "Article Y",
                    "translated_titles": translated_titles,
                }
            )

            # Acessa o TOC diretamente com idioma en na URL
            toc_url_en = url_for(
                "main.issue_toc",
                url_seg=journal.url_segment,
                url_seg_issue=issue.url_segment,
                lang="en",
            )
            response = c.get(toc_url_en)

            self.assertEqual(200, response.status_code)
            self.assertIn(b'lang="en"', response.data)
            self.assertIn("Article Y", response.data.decode("utf-8"))

    def test_the_title_of_the_article_list_without_unknow_language_for_article(self):
        """
        Teste para verificar se a interface do TOC esta retornando o título no
        idioma original quando não conhece o idioma.
        """
        journal = utils.makeOneJournal()

        with self.client as c:
            # Criando uma coleção para termos o objeto ``g`` na interface
            utils.makeOneCollection()

            issue = utils.makeOneIssue({"journal": journal})

            translated_titles = []

            utils.makeOneArticle(
                {
                    "issue": issue,
                    "title": "Article Y",
                    "translated_titles": translated_titles,
                }
            )

            # Acessa o TOC diretamente com idioma es na URL
            toc_url_es = url_for(
                "main.issue_toc",
                url_seg=journal.url_segment,
                url_seg_issue=issue.url_segment,
                lang="es",
            )
            response = c.get(toc_url_es)

            self.assertEqual(200, response.status_code)
            self.assertIn(b'lang="es"', response.data)
            self.assertIn("Article Y", response.data.decode("utf-8"))

    def test_the_title_of_the_article_list_with_and_without_translated(self):
        """
        Teste para verificar se a interface do TOC esta retornando o título no
        idioma original para artigos que não tem tradução e o título traduzido
        quando tem tradução do título.
        """
        journal = utils.makeOneJournal()

        with self.client as c:
            # Criando uma coleção para termos o objeto ``g`` na interface
            utils.makeOneCollection()

            issue = utils.makeOneIssue({"journal": journal})

            translated_titles = [
                {"name": "Artigo Com Título Em Português", "language": "pt"},
                {"name": "Título Del Artículo En Portugués", "language": "es"},
                {"name": "Article Title In Portuguese", "language": "en"},
            ]

            utils.makeOneArticle(
                {
                    "issue": issue,
                    "title": "Article Y",
                    "translated_titles": translated_titles,
                }
            )

            utils.makeOneArticle(
                {"issue": issue, "title": "Article Y", "translated_titles": []}
            )

            # Acessa o TOC diretamente com idioma es na URL
            toc_url_es = url_for(
                "main.issue_toc",
                url_seg=journal.url_segment,
                url_seg_issue=issue.url_segment,
                lang="es",
            )
            response = c.get(toc_url_es)

            self.assertEqual(200, response.status_code)
            self.assertIn(b'lang="es"', response.data)
            self.assertIn("Article Y", response.data.decode("utf-8"))
            self.assertIn(
                "Título Del Artículo En Portugués", response.data.decode("utf-8")
            )

    def test_ahead_of_print_is_displayed_at_table_of_contents(self):
        """
        Teste para verificar se caso o issue for um ahead o valor da legenda bibliográfica é alterada para 'ahead of print'.
        """
        journal = utils.makeOneJournal()

        with self.client as c:
            # Criando uma coleção para termos o objeto ``g`` na interface
            utils.makeOneCollection()

            issue = utils.makeOneIssue({"journal": journal, "type": "ahead"})

            response = c.get(
                url_for(
                    "main.aop_toc",
                    url_seg=journal.url_segment,
                    url_seg_issue=issue.url_segment,
                )
            )

            self.assertIn("ahead of print", response.data.decode("utf-8"))

    def test_abstract_links_are_displayed(self):
        """
        Teste para verificar se caso o issue for um ahead o valor da
        legenda bibliográfica é alterada para 'ahead of print'.
        """
        journal = utils.makeOneJournal()

        with self.client as c:
            # Criando uma coleção para termos o objeto ``g`` na interface
            utils.makeOneCollection()

            issue = utils.makeOneIssue({"journal": journal})

            _article_data = {
                "title": "Article Y",
                "original_language": "en",
                "languages": ["es", "pt", "en"],
                "issue": issue,
                "journal": journal,
                "abstract_languages": ["en", "es", "pt"],
                "url_segment": "10-11",
                "translated_titles": [
                    {"language": "es", "name": "Artículo en español"},
                    {"language": "pt", "name": "Artigo en Português"},
                ],
                "pid": "pidv2",
            }
            article = utils.makeOneArticle(_article_data)

            response = c.get(
                url_for(
                    "main.issue_toc",
                    url_seg=journal.url_segment,
                    url_seg_issue=issue.url_segment,
                    lang="pt",
                )
            )

            # Links do abstract podem ser path ou path + ?lang= (view exige lang na query)
            for abstract_lang in ["en", "es", "pt"]:
                path = url_for(
                    "main.article_detail_v3",
                    url_seg=journal.url_segment,
                    article_pid_v3=article.aid,
                    part="abstract",
                    lang=abstract_lang,
                )
                with self.subTest(abstract_lang):
                    self.assertTrue(
                        path in response.data.decode("utf-8")
                        or (path + "?lang=" + abstract_lang) in response.data.decode("utf-8"),
                        "Abstract link for lang=%s not found" % abstract_lang,
                    )

    def test_author_search_link_includes_orcid_when_authors_meta_has_orcid(self):
        """
        Teste para verificar se o link de busca do autor inclui o orcid
        quando o artigo tem authors_meta com orcid.
        """
        journal = utils.makeOneJournal()

        with self.client as c:
            utils.makeOneCollection()

            issue = utils.makeOneIssue({"journal": journal})

            _article_data = {
                "title": "Article Y",
                "issue": issue,
                "journal": journal,
                "authors": ["Author One", "Author Two"],
                "authors_meta": [
                    {
                        "name": "Author One",
                        "affiliation": "University A",
                        "orcid": "0000-0002-3430-5422",
                    },
                    {
                        "name": "Author Two",
                        "affiliation": "University B",
                    },
                ],
            }
            utils.makeOneArticle(_article_data)

            response = c.get(
                url_for(
                    "main.issue_toc",
                    url_seg=journal.url_segment,
                    url_seg_issue=issue.url_segment,
                    lang="pt",
                )
            )

            response_data = response.data.decode("utf-8")

            # Author with ORCID should have orcid OR au:(name) in the search query
            self.assertIn(
                "q=orcid:0000-0002-3430-5422 OR au:(Author One)",
                response_data,
            )
            # Author without ORCID should only have au:name in the search query
            self.assertIn("q=au:Author Two", response_data)
            self.assertNotIn("orcid:Author Two", response_data)
            self.assertNotIn("OR au:(Author Two)", response_data)
            # Author search links should open in a new tab
            self.assertIn('target="_blank"', response_data)

    def test_author_search_link_without_orcid_when_no_authors_meta(self):
        """
        Teste para verificar se o link de busca do autor funciona sem orcid
        quando o artigo não tem authors_meta (fallback para authors).
        """
        journal = utils.makeOneJournal()

        with self.client as c:
            utils.makeOneCollection()

            issue = utils.makeOneIssue({"journal": journal})

            _article_data = {
                "title": "Article Z",
                "issue": issue,
                "journal": journal,
                "authors": ["Simple Author"],
            }
            utils.makeOneArticle(_article_data)

            response = c.get(
                url_for(
                    "main.issue_toc",
                    url_seg=journal.url_segment,
                    url_seg_issue=issue.url_segment,
                    lang="pt",
                )
            )

            response_data = response.data.decode("utf-8")

            self.assertIn("q=au:Simple Author", response_data)
            self.assertNotIn("orcid:", response_data)
            # Author search links should open in a new tab
            self.assertIn('target="_blank"', response_data)
