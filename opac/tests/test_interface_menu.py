# coding: utf-8

from flask import current_app, url_for
from flask_babelex import lazy_gettext as __

from . import utils
from .base import BaseTestCase


class MenuTestCase(BaseTestCase):
    # Collection Menu

    def test_alpha_link_is_selected_for_list_alpha(self):
        """
        Verficamos que o link do menú "Alfabética" tem o css:
        "selected" quando acessamos a view "collection_list_alpha"
        """
        response = self.client.get(url_for("main.collection_list", lang="pt"))

        self.assertStatus(response, 200)
        self.assertTemplateUsed("collection/list_journal.html")
        # Na lista alfabética, a aba alpha está ativa (nav-link active alpha-tab)
        response_data = response.data.decode("utf-8")
        self.assertIn("alpha-tab", response_data)
        self.assertIn("nav-link active", response_data)
        self.assertIn("journals/alpha", response_data)

    def test_theme_link_is_selected_for_list_theme(self):
        """
        Verficamos que o link do menú "Temática" tem o css:
        "selected" quando acessamos a view "collection_list_theme"
        """
        response = self.client.get(url_for("main.collection_list_thematic", lang="pt"))

        self.assertStatus(response, 200)
        self.assertTemplateUsed("collection/list_thematic.html")
        # Na lista temática, a aba thematic está ativa (nav-link active thematic-tab)
        response_data = response.data.decode("utf-8")
        self.assertIn("thematic-tab", response_data)
        self.assertIn("nav-link active", response_data)
        self.assertIn("journals/thematic", response_data)

    # Hamburger Menu
    def test_links_in_hamburger_menu(self):
        """
        no menú de hamurger, verificamos os links que apontam a views do opac
        """
        with current_app.app_context():
            collection = utils.makeOneCollection({"name": "dummy collection"})

            with self.client as c:
                response = c.get(url_for("main.index", lang="pt"))
                response_data = response.data.decode("utf-8")
                self.assertStatus(response, 200)
                # Nome da coleção e link para a home (com idioma no path)
                self.assertIn(
                    collection.name or str(__("NOME DA COLEÇÃO!!")), response_data
                )
                self.assertIn('href="/pt/"', response_data)
                self.assertIn("dummy collection", response_data)
                # Lista alfabética e temática
                self.assertIn("journals/alpha?status=current", response_data)
                self.assertIn(str(__("Lista alfabética de periódicos")), response_data)
                self.assertIn("journals/thematic?status=current", response_data)
                self.assertIn(str(__("Lista temática de periódicos")), response_data)
                # Busca
                self.assertIn("search.scielo.org", response_data)
                self.assertIn("Busca", response_data)
                # Métricas
                self.assertIn(current_app.config["METRICS_URL"], response_data)
                self.assertIn(str(__("Métricas")), response_data)
                # Sobre e Contatos
                self.assertIn("/pt/about/", response_data)
                self.assertIn(str(__("Sobre o SciELO")), response_data)
                self.assertIn(str(__("Contatos")), response_data)
                # SciELO.org
                self.assertIn("//www.scielo.org", response_data)
                self.assertIn("SciELO.org - Rede SciELO", response_data)
                self.assertIn(str(__("Coleções nacionais e temáticas")), response_data)
                self.assertIn("listar-por-ordem-alfabetica", response_data)
                self.assertIn("listar-por-assunto", response_data)
                self.assertIn(str(__("Lista de periódicos por assunto")), response_data)
                self.assertIn("sobre-o-scielo/acesso-via-oai-e-rss", response_data)
                self.assertIn(str(__("Acesso OAI e RSS")), response_data)
                self.assertIn("sobre-o-scielo/", response_data)
                self.assertIn(str(__("Sobre a Rede SciELO")), response_data)
                self.assertIn("sobre-o-scielo/contato", response_data)

    def test_blog_link_in_hamburger_menu(self):
        """
        Verificamos que o link para o blog em perspectiva fique
        apontando ao link certo considerando o idioma da sessão
        """

        with current_app.app_context():
            utils.makeOneCollection(
                {
                    "name_pt": "coleção falsa",
                    "name_es": "coleccion falsa",
                    "name_en": "dummy collection",
                }
            )

            with self.client as c:
                # idioma em 'pt_br'
                response = c.get(
                    url_for("set_locale", ilang="pt_BR"),
                    headers={"Referer": "/"},
                    follow_redirects=True,
                )

                self.assertStatus(response, 200)
                expected_anchor_tag = '<a target="_blank" href="%s">'
                expected_anchor = expected_anchor_tag % (
                    current_app.config["URL_BLOG_SCIELO"]
                )
                self.assertIn(expected_anchor, response.data.decode("utf-8"))

                # idioma em 'en'
                response = c.get(
                    url_for("set_locale", ilang="en"),
                    headers={"Referer": "/"},
                    follow_redirects=True,
                )

                self.assertStatus(response, 200)
                expected_anchor = expected_anchor_tag % (
                    current_app.config["URL_BLOG_SCIELO"] + "/en/"
                )
                self.assertIn(expected_anchor, response.data.decode("utf-8"))

                # idioma em 'es'
                response = c.get(
                    url_for("set_locale", ilang="es"),
                    headers={"Referer": "/"},
                    follow_redirects=True,
                )

                self.assertStatus(response, 200)
                expected_anchor = expected_anchor_tag % (
                    current_app.config["URL_BLOG_SCIELO"] + "/es/"
                )
                self.assertIn(expected_anchor, response.data.decode("utf-8"))

    # Journal Menu
    def test_journal_detail_menu(self):
        """
        Teste para verificar se os botões estão ``anterior``, ``atual``,
        ``próximo`` estão disponíveis no ``journal/detail.html``
        """
        with current_app.app_context():
            # Criando uma coleção para termos o objeto ``g`` na interface
            utils.makeOneCollection()

            last_issue = utils.getLastIssue(
                {
                    "year": "2016",
                    "volume": "1",
                    "number": "3",
                    "order": "3",
                }
            )
            journal = utils.makeOneJournal({"last_issue": last_issue})

            response = self.client.get(
                url_for("main.journal_detail", url_seg=journal.url_segment, lang="pt")
            )

            self.assertStatus(response, 200)
            self.assertTemplateUsed("journal/detail.html")

            response_data = response.data.decode("utf-8")
            # Com um único número: anterior e seguinte desabilitados; atual com link
            self.assertIn('title="número anterior"', response_data)
            self.assertIn('title="número seguinte"', response_data)
            self.assertIn('title="número atual"', response_data)
            # Anterior e seguinte desabilitados (um único issue)
            self.assertIn('número anterior', response_data)
            self.assertIn('href="#"', response_data)
            self.assertIn("disabled", response_data)
            # Link do número atual aponta para o TOC do issue (path pode ter prefixo de idioma /pt/j/...)
            issue_toc_path = "/j/%s/i/%s" % (journal.url_segment, last_issue.url_segment)
            self.assertIn(issue_toc_path, response_data)

    def test_journal_detail_menu_without_issues(self):
        """
        Teste para verificar se os botões estão ``anterior``, ``atual``,
        ``próximo`` estão disponíveis no ``jorunal/detail.html`` quando o periódico
        não tem número.
        """
        journal = utils.makeOneJournal()

        with current_app.app_context():
            # Criando uma coleção para termos o objeto ``g`` na interface
            utils.makeOneCollection()

            response = self.client.get(
                url_for("main.journal_detail", url_seg=journal.url_segment, lang="pt")
            )

            self.assertStatus(response, 200)
            self.assertTemplateUsed("journal/detail.html")

            # Sem números: botões anterior/seguinte desabilitados (template usa "btn disabled")
            response_data = response.data.decode("utf-8")
            self.assertIn("disabled", response_data)
            self.assertIn('href="#"', response_data)

    def test_journal_detail_menu_with_one_issue(self):
        """
        Teste para verificar se os botões estão ``anterior``, ``atual``,
        ``próximo`` estão disponíveis no ``jorunal/detail.html`` quando o periódico
        tem um número o botão ``próximo`` e ``anterior`` deve vir desabilitados.
        """
        with current_app.app_context():
            # Criando uma coleção para termos o objeto ``g`` na interface
            utils.makeOneCollection()

            last_issue = utils.getLastIssue(
                {
                    "year": "2016",
                    "volume": "1",
                    "number": "10",
                    "order": "10",
                    "suppl_text": "",
                }
            )
            journal = utils.makeOneJournal({"last_issue": last_issue})
            issues = [
                utils.makeOneIssue(
                    {
                        "year": "2016",
                        "volume": "1",
                        "number": str(number),
                        "order": str(number),
                        "suppl_text": "",
                        "journal": journal._id,
                    }
                )
                for number in (10,)
            ]
            issue_toc_url = url_for(
                "main.issue_toc",
                url_seg=journal.url_segment,
                url_seg_issue=issues[0].url_segment,
                lang="pt",
            )

            response = self.client.get(issue_toc_url)
            self.assertStatus(response, 200)
            self.assertTemplateUsed("issue/toc.html")
            # Um único issue: anterior e seguinte desabilitados; atual com link
            resp = response.data.decode("utf-8")
            self.assertIn("número anterior", resp)
            self.assertIn("número atual", resp)
            self.assertIn("número seguinte", resp)
            self.assertIn("/j/%s/i/%s" % (journal.url_segment, last_issue.url_segment), resp)
            self.assertIn("disabled", resp)
            self.assertIn('href="#"', resp)

    def test_journal_detail_menu_access_issue_toc_on_any_issue(self):
        """
        Teste para verificar se os botões estão ``anterior``, ``atual``,
        ``próximo`` estão disponíveis no ``jorunal/detail.html``, quando acessamos
        qualquer número.
        """
        with current_app.app_context():
            # Criando uma coleção para termos o objeto ``g`` na interface
            utils.makeOneCollection()

            last_issue = utils.getLastIssue(
                {
                    "year": "2016",
                    "volume": "1",
                    "number": "10",
                    "order": "10",
                    "suppl_text": "",
                }
            )
            journal = utils.makeOneJournal({"last_issue": last_issue})
            issues = [
                utils.makeOneIssue(
                    {
                        "year": "2016",
                        "volume": "1",
                        "number": str(number),
                        "order": str(number),
                        "suppl_text": "",
                        "journal": journal._id,
                    }
                )
                for number in (1, 2, 10)
            ]
            issue_toc_url = url_for(
                "main.issue_toc",
                url_seg=journal.url_segment,
                url_seg_issue=issues[1].url_segment,
                lang="pt",
            )

            response = self.client.get(issue_toc_url)
            self.assertStatus(response, 200)
            self.assertTemplateUsed("issue/toc.html")
            # No issue do meio: anterior, atual e seguinte com links
            resp = response.data.decode("utf-8")
            self.assertIn("número anterior", resp)
            self.assertIn("número atual", resp)
            self.assertIn("número seguinte", resp)
            self.assertIn(issues[0].url_segment, resp)
            self.assertIn(issues[1].url_segment, resp)
            self.assertIn(last_issue.url_segment, resp)

    def test_journal_detail_menu_access_issue_toc_lastest_issue(self):
        """
        Teste para verificar se os botões estão ``anterior``, ``atual``,
        ``próximo`` estão disponíveis no ``jorunal/detail.html``, quando acessamos
        o número mais recente.
        """

        with current_app.app_context():
            # Criando uma coleção para termos o objeto ``g`` na interface
            utils.makeOneCollection()

            last_issue = utils.getLastIssue(
                {
                    "year": "2016",
                    "volume": "1",
                    "number": "3",
                    "order": "3",
                    "suppl_text": "",
                }
            )
            journal = utils.makeOneJournal({"last_issue": last_issue})
            issue = utils.makeOneIssue(
                {
                    "year": "2016",
                    "volume": "1",
                    "number": "3",
                    "order": "3",
                    "suppl_text": "",
                    "journal": journal._id,
                }
            )

            issue_toc_url = url_for(
                "main.issue_toc",
                url_seg=journal.url_segment,
                url_seg_issue=last_issue.url_segment,
                lang="pt",
            )

            response = self.client.get(issue_toc_url)
            self.assertStatus(response, 200)
            self.assertTemplateUsed("issue/toc.html")
            # No número mais recente: anterior com link, siguiente desabilitado
            resp = response.data.decode("utf-8")
            self.assertIn("número anterior", resp)
            self.assertIn("número atual", resp)
            self.assertIn("número seguinte", resp)
            self.assertIn("/j/%s/i/%s" % (journal.url_segment, last_issue.url_segment), resp)
            self.assertIn("disabled", resp)

    def test_journal_detail_menu_access_issue_toc_oldest_issue(self):
        """
        Teste para verificar se os botões estão ``anterior``, ``atual``,
        ``próximo`` estão disponíveis no ``jorunal/detail.html``, quando acessamos
        o número mais antigo.
        """
        with current_app.app_context():
            # Criando uma coleção para termos o objeto ``g`` na interface
            utils.makeOneCollection()

            last_issue = utils.getLastIssue(
                {
                    "year": "2016",
                    "volume": "1",
                    "number": "10",
                    "order": "10",
                    "suppl_text": "",
                }
            )
            journal = utils.makeOneJournal({"last_issue": last_issue})
            issues = [
                utils.makeOneIssue(
                    {
                        "year": "2016",
                        "volume": "1",
                        "number": str(number),
                        "order": str(number),
                        "suppl_text": "",
                        "journal": journal._id,
                    }
                )
                for number in (1, 2, 10)
            ]
            issue_toc_url = url_for(
                "main.issue_toc",
                url_seg=journal.url_segment,
                url_seg_issue=issues[0].url_segment,
                lang="pt",
            )

            response = self.client.get(issue_toc_url)
            self.assertStatus(response, 200)
            self.assertTemplateUsed("issue/toc.html")
            # No número mais antigo: anterior desabilitado, siguiente e atual com links
            resp = response.data.decode("utf-8")
            self.assertIn("número anterior", resp)
            self.assertIn("número atual", resp)
            self.assertIn("número seguinte", resp)
            self.assertIn(issues[0].url_segment, resp)
            self.assertIn(last_issue.url_segment, resp)
            self.assertIn("disabled", resp)
