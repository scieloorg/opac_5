# coding: utf-8

import os
import tempfile
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup, element
from flask import current_app, url_for
from webapp.utils.journal_static_page import (
    OldJournalPageFile,
    child_tostring,
    has_footer,
    has_header,
    remove_exceding_space_chars,
    wrap,
)

from . import utils
from .base import BaseTestCase

REVISTAS_PATH = "opac/tests/fixtures/pages/revistas"
IMG_REVISTAS_PATH = "opac/tests/fixtures/pages/img_revistas"


class OldJournalPageTestCase(BaseTestCase):
    def html_file(self, name):
        f = os.path.join(REVISTAS_PATH, name.replace("_", "/") + ".htm")
        if os.path.isfile(f):
            return f

    def write_temp_html(self, acron, filename, content, encoding="utf-8"):
        tmpdir = tempfile.mkdtemp()
        journal_dir = os.path.join(tmpdir, acron)
        os.makedirs(journal_dir)
        path = os.path.join(journal_dir, filename)
        with open(path, "w", encoding=encoding) as f:
            f.write(content)
        return path

    def test_title_icse_eaboutj(self):
        jspf = OldJournalPageFile(self.html_file("icse_eaboutj"))
        self.assertEqual(jspf.acron, "icse")
        self.assertEqual(jspf.anchor_title, "<h1>Acerca de la revista</h1>")
        self.assertTrue("<h1>Acerca de la revista</h1>" in jspf.body)

    def test_title_eins_eedboar(self):
        jspf = OldJournalPageFile(self.html_file("eins_eedboard"))
        self.assertEqual(jspf.anchor_title, "<h1>Cuerpo Editorial</h1>")
        self.assertTrue("<h1>Cuerpo Editorial</h1>" in jspf.body)

    def test_title_abb_einstruc(self):
        jspf = OldJournalPageFile(self.html_file("abb_einstruc"))
        self.assertEqual(jspf.anchor_title, "<h1>Instrucciones a los autores</h1>")
        self.assertTrue("<h1>Instrucciones a los autores</h1>" in jspf.body)

    def test_title_bjgeo_einstr(self):
        jspf = OldJournalPageFile(self.html_file("bjgeo_einstruct"))
        self.assertEqual(jspf.anchor_title, "<h1>Instrucciones a los autores</h1>")
        self.assertTrue("<h1>Instrucciones a los autores</h1>" in jspf.body)

    def test_title_bjmbr_pabout(self):
        jspf = OldJournalPageFile(self.html_file("bjmbr_paboutj"))
        self.assertEqual(jspf.anchor_title, "<h1>Sobre o periódico</h1>")
        self.assertTrue("<h1>Sobre o periódico</h1>" in jspf.body)

    def test_title_eagri_pedboa(self):
        jspf = OldJournalPageFile(self.html_file("eagri_pedboard"))
        self.assertEqual(jspf.anchor_title, "<h1>Corpo Editorial</h1>")
        self.assertTrue("<h1>Corpo Editorial</h1>" in jspf.body)

    def test_title_abb_pinstruc(self):
        jspf = OldJournalPageFile(self.html_file("abb_pinstruc"))
        self.assertEqual(jspf.anchor_title, "<h1>Instruções aos autores</h1>")
        self.assertTrue("<h1>Instruções aos autores</h1>" in jspf.body)

    def test_title_bjgeo_pinstr(self):
        jspf = OldJournalPageFile(self.html_file("bjgeo_pinstruct"))
        self.assertEqual(jspf.anchor_title, "<h1>Instruções aos autores</h1>")
        self.assertTrue("<h1>Instruções aos autores</h1>" in jspf.body)

    def test_title_bjmbr_iabout(self):
        jspf = OldJournalPageFile(self.html_file("bjmbr_iaboutj"))
        self.assertEqual(jspf.anchor_title, "<h1>About the journal</h1>")
        self.assertTrue("<h1>About the journal</h1>" in jspf.body)

    def test_title_bjmbr_iedboa(self):
        jspf = OldJournalPageFile(self.html_file("bjmbr_iedboard"))
        self.assertEqual(jspf.anchor_title, "<h1>Editorial Board</h1>")
        self.assertTrue("<h1>Editorial Board</h1>" in jspf.body)

    def test_title_bjmbr_iinstr(self):
        jspf = OldJournalPageFile(self.html_file("bjmbr_iinstruc"))
        self.assertEqual(jspf.anchor_title, "<h1>Instructions to authors</h1>")
        self.assertTrue("<h1>Instructions to authors</h1>" in jspf.body)

    def test_insert_bold_to_p_subtitulo_aa_eedboard(self):
        jspf = OldJournalPageFile(self.html_file("aa_eedboard"))

        self.assertEqual(jspf.body_content.count('class="subtitulo"'), 4)
        self.assertTrue(
            '<p class="subtitulo"><a name="001">Editor-Jefe</a></p>'
            in jspf.body_content
        )
        self.assertTrue(
            '<p class="subtitulo"><a name="0011"></a>Editor-Jefe Sustituto</p>'
            in jspf.body_content
        )
        self.assertTrue(
            '<p class="subtitulo">Comisión editorial</p>' in jspf.body_content
        )
        jspf._insert_bold_to_p_subtitulo()
        self.assertEqual(jspf.body_content.count('class="subtitulo"'), 0)
        self.assertTrue("<p><b>Comisión editorial</b></p>" in jspf.body_content)
        self.assertTrue(
            '<p><b><a name="001">Editor-Jefe</a></b></p>' in jspf.body_content
        )
        self.assertTrue(
            '<p><a name="0011"></a><b>Editor-Jefe Sustituto</b></p>'
            in jspf.body_content
        )

    def test_remove_anchors_abb_pinstruc(self):
        jspf = OldJournalPageFile(self.html_file("abb_pinstruc"))
        self.assertTrue('<a name="end"></a>' in jspf.body_content)
        jspf._remove_anchors()
        self.assertTrue('<a name="end"></a>' not in jspf.body_content)

    def test_remove_anchors_aa_eedboard(self):
        jspf = OldJournalPageFile(self.html_file("aa_eedboard"))

        self.assertEqual(jspf.body_content.count('class="subtitulo"'), 4)
        self.assertTrue(
            '<p class="subtitulo"><a name="001">Editor-Jefe</a></p>'
            in jspf.body_content
        )
        self.assertTrue(
            '<p class="subtitulo"><a name="0011"></a>Editor-Jefe Sustituto</p>'
            in jspf.body_content
        )

        self.assertTrue('<a name="0011"' in jspf.body_content)
        jspf._remove_anchors()
        self.assertTrue(
            '<p class="subtitulo">Editor-Jefe Sustituto</p>' in jspf.body_content
        )

    def test_middle_text_ea_pinstruc(self):
        jspf = OldJournalPageFile(self.html_file("ea_pinstruc"))
        text = "<p>6. As Referências bibliográficas deverão ser citadas"
        self.assertTrue(text in jspf.middle_text)

    def test_read_iso_8859_1_eagri_pedboard(self):
        jspf = OldJournalPageFile(self.html_file("eagri_pedboard"))
        self.assertTrue("Agrícola" in jspf.body_content)
        self.assertTrue("Associação" in jspf.body_content)

    def test_insert_middle_begin_abb_pinstruc(self):
        jspf = OldJournalPageFile(self.html_file("abb_pinstruc"))
        self.assertTrue("Editable" in jspf.body_content)
        self.assertFalse('"middle_begin"' in jspf.body_content)
        jspf.insert_p_middle_begin()
        self.assertTrue('"middle_begin"' in jspf.body_content)

    def test_insert_middle_begin_aa_eedboard(self):
        jspf = OldJournalPageFile(self.html_file("aa_eedboard"))
        self.assertTrue('href="#0' in jspf.body_content)
        self.assertFalse('"middle_begin"' in jspf.body_content)
        jspf.insert_p_middle_begin()
        self.assertTrue('"middle_begin"' in jspf.body_content)

    def test_insert_middle_begin_ea_iinstruc(self):
        jspf = OldJournalPageFile(self.html_file("ea_iinstruc"))
        self.assertTrue("script=sci_serial" in jspf.body_content)
        self.assertFalse('"middle_begin"' in jspf.body_content)
        jspf.insert_p_middle_begin()
        self.assertTrue('"middle_begin"' in jspf.body_content)

    def test_insert_middle_begin_eins_eedboard(self):
        jspf = OldJournalPageFile(self.html_file("eins_eedboard"))
        self.assertTrue("/scielo.php?lng=" in jspf.body_content)
        self.assertFalse('"middle_begin"' in jspf.body_content)
        jspf.insert_p_middle_begin()
        self.assertTrue('"middle_begin"' in jspf.body_content)

    def test_middle_end_abb_pinstruc(self):
        jspf = OldJournalPageFile(self.html_file("abb_pinstruc"))
        self.assertTrue("javascript:history.back()" in jspf.body_content)
        self.assertFalse('"middle_end"' in jspf.body_content)
        jspf.insert_p_middle_end()
        self.assertTrue('"middle_end"' in jspf.body_content)
        self.assertTrue(jspf.p_middle_end is not None)

    def test_insert_middle_end_aa_eedboard(self):
        jspf = OldJournalPageFile(self.html_file("aa_eedboard"))
        self.assertTrue("script=sci_serial" in jspf.body_content)
        self.assertTrue("Home" in jspf.body_content)
        self.assertFalse('"middle_end"' in jspf.body_content)
        jspf.insert_p_middle_end()
        self.assertTrue('"middle_end"' in jspf.body_content)
        self.assertTrue(jspf.p_middle_end is not None)

    def test_insert_middle_end_bjmbr_iedboard(self):
        jspf = OldJournalPageFile(self.html_file("bjmbr_iedboard"))
        self.assertTrue("script=sci_serial" in jspf.body_content)
        self.assertTrue("Home" in jspf.body_content)

        self.assertNotIn('"middle_end"', jspf.file_content)
        jspf.insert_p_middle_end()
        self.assertTrue('"middle_end"' in jspf.body_content)
        self.assertTrue(jspf.p_middle_end is not None)

    def test_insert_middle_end_bjgeo_pinstruct(self):
        jspf = OldJournalPageFile(self.html_file("bjgeo_pinstruct"))
        self.assertTrue("script=sci_serial" in jspf.body_content)
        self.assertTrue("Voltar" in jspf.body_content)
        self.assertFalse('"middle_end"' in jspf.body_content)
        jspf.insert_p_middle_end()
        self.assertTrue('"middle_end"' in jspf.body_content)
        self.assertTrue(jspf.p_middle_end is not None)

    def test_insert_middle_end_bjgeo_einstruct(self):
        jspf = OldJournalPageFile(self.html_file("bjgeo_einstruct"))
        self.assertTrue("script=sci_serial" in jspf.body_content)
        self.assertTrue("Volver" in jspf.body_content)
        self.assertFalse('"middle_end"' in jspf.body_content)
        jspf.insert_p_middle_end()
        self.assertTrue('"middle_end"' in jspf.body_content)
        self.assertTrue(jspf.p_middle_end is not None)

    @unittest.skip(
        "Teste não tem comportamento consistente entre o travis e o ambiente de desenvolvimento."
    )
    def test_insert_middle_end_bjmbr_iinstruct(self):
        jspf = OldJournalPageFile(self.html_file("bjmbr_iinstruc"))
        self.assertEqual(jspf.file_content.count("script=sci_serial"), 3)
        self.assertTrue("Home" in jspf.file_content)
        self.assertFalse('"middle_end"' in jspf.body_content)
        jspf.insert_p_middle_end()
        self.assertFalse('"middle_end"' in jspf.body_content)
        self.assertTrue(jspf.p_middle_end is None)
        middle = jspf.middle.strip()
        begin = '<!-- #BeginEditable "texto" -->'
        end = "<p>&nbsp;</p>"
        self.assertEqual(middle[-len(end) :], end)
        self.assertEqual(middle[: len(begin)], begin)

    def test_insert_middle_end_bjmbr_iaboutj(self):
        jspf = OldJournalPageFile(self.html_file("bjmbr_iaboutj"))
        self.assertEqual(len(jspf._body_tree.find_all("li")), 17)
        self.assertEqual(len(jspf._body_tree.find_all("p")), 38)
        self.assertIn(
            "<P>Sociedade Brasileira de Biologia Celular (SBBC) </p>", jspf.file_content
        )
        self.assertEqual(jspf.body.count("<li>"), 13)
        self.assertEqual(jspf.body.count("<p>"), 10)
        self.assertNotIn(
            "<P>Sociedade Brasileira de Biologia Celular (SBBC) </p>", jspf.body_content
        )

    def test_unavailable_msg_es_abb_einstruc(self):
        jspf = OldJournalPageFile(self.html_file("abb_einstruc"))
        self.assertTrue(jspf.ES_UNAVAILABLE_MSG in jspf.unavailable_message)

    def test_unavailable_message_pt_abb_pinstruc(self):
        jspf = OldJournalPageFile(self.html_file("abb_pinstruc"))
        self.assertTrue(jspf.PT_UNAVAILABLE_MSG in jspf.unavailable_message)

    def _in_antes_e_depois(self, file_content, body, antes, depois):
        self.assertIn(antes, file_content)
        self.assertNotIn(depois, file_content)
        self.assertNotIn(antes, body)
        self.assertIn(depois, body)

    def _count_antes_e_depois(self, file_content, body, text, antes=0, depois=0):
        self.assertEqual(file_content.count(text), antes)
        self.assertEqual(body.count(text), depois)

    def test_legacy_info_page_iaboutj(self):
        """
        Teste da ``view function`` ``router_legacy_info_pages``, deve retorna status_code 301 para a página iaboutj
        """

        with current_app.app_context():
            utils.makeOneCollection()

            journal = utils.makeOneJournal(
                {"title": "Revista X", "acronym": "acron_ia"}
            )

            response = self.client.get("/revistas/%s/iaboutj.htm" % journal.url_segment)

            self.assertTrue(301, response.status_code)

    def test_legacy_info_page_edboard(self):
        """
        Teste da ``view function`` ``router_legacy_info_pages``, deve retorna status_code 301 para a página edboard
        """

        with current_app.app_context():
            utils.makeOneCollection()

            journal = utils.makeOneJournal(
                {"title": "Revista X", "acronym": "acron_ed"}
            )

            response = self.client.get("/revistas/%s/edboard.htm" % journal.url_segment)

            self.assertTrue(301, response.status_code)

    def test_legacy_info_page_iinstruc(self):
        """
        Teste da ``view function`` ``router_legacy_info_pages``, deve retorna status_code 301 para a página iinstruc
        """

        with current_app.app_context():
            utils.makeOneCollection()

            journal = utils.makeOneJournal(
                {"title": "Revista X", "acronym": "acron_ii"}
            )

            response = self.client.get(
                "/revistas/%s/iinstruc.htm" % journal.url_segment
            )

            self.assertTrue(301, response.status_code)

    def test_legacy_info_page_isubscrp(self):
        """
        Teste da ``view function`` ``router_legacy_info_pages``, deve retorna status_code 301 para a página isubscrp
        """

        with current_app.app_context():
            utils.makeOneCollection()

            journal = utils.makeOneJournal(
                {"title": "Revista X", "acronym": "acron_isu"}
            )

            response = self.client.get(
                "/revistas/%s/isubscrp.htm" % journal.url_segment
            )

            self.assertTrue(301, response.status_code)

    def test_has_header_and_has_footer_helpers(self):
        self.assertTrue(has_header("Editable <!-- comment -->"))
        self.assertTrue(has_header('href="#001"'))
        self.assertTrue(has_header("script=sci_serial"))
        self.assertTrue(has_header("/scielo.php?lng=pt"))
        self.assertFalse(has_header("plain table content"))

        mock_a = type("A", (), {"text": "Home"})()
        self.assertTrue(has_footer("#", mock_a))
        self.assertTrue(has_footer("script=sci_serial&lng=pt", mock_a))
        mock_a.text = "Voltar"
        self.assertTrue(has_footer("script=sci_serial", mock_a))
        mock_a.text = "Volver"
        self.assertTrue(has_footer("script=sci_serial", mock_a))
        mock_a.text = "Home"
        self.assertTrue(has_footer("javascript:history.back()"))

        self.assertTrue(has_footer("script=sci_serial&Home=1"))
        self.assertTrue(has_footer("script=sci_serial&Voltar=1"))
        self.assertTrue(has_footer("script=sci_serial&Volver=1"))
        self.assertTrue(has_footer("javascript:history.back()"))
        self.assertFalse(has_footer("other-link"))

    def test_remove_exceding_space_chars(self):
        self.assertEqual(
            remove_exceding_space_chars("  hello   world  "), "hello world"
        )

    def test_child_tostring_and_wrap(self):
        soup = BeautifulSoup("<p><b>text</b></p>", "html.parser")
        tag = soup.find("b")
        self.assertEqual("text", child_tostring(tag))
        self.assertEqual("plain", child_tostring(element.NavigableString("plain")))

        new_tag = soup.new_tag("i")
        wrap(tag, new_tag)
        self.assertEqual("<i><b>text</b></i>", str(tag.parent))

        p = soup.new_tag("p")
        text_node = element.NavigableString("wrapped")
        p.append(text_node)
        wrapped = wrap(text_node, soup.new_tag("em"))
        self.assertEqual("<em>wrapped</em>", str(wrapped))

        nested = BeautifulSoup("<p><b><span>x</span></b></p>", "html.parser").find("b")
        wrap(nested, soup.new_tag("strong"))

        self.assertIsNone(child_tostring(object()))

    def test_read_file_not_found_logs_error(self):
        missing = os.path.join(tempfile.gettempdir(), "missing_journal", "iaboutj.htm")
        jspf = OldJournalPageFile(missing)
        self.assertEqual("", jspf.file_content)

    def test_read_generic_exception(self):
        path = self.write_temp_html("x", "iaboutj.htm", "<html></html>")
        with patch(
            "webapp.utils.journal_static_page.open",
            side_effect=PermissionError("denied"),
        ):
            jspf = OldJournalPageFile(path)
        self.assertEqual("", jspf.file_content)

    def test_tree_content_when_tree_is_none(self):
        jspf = OldJournalPageFile(self.html_file("bjmbr_iaboutj"))
        jspf.tree = None
        self.assertEqual(jspf.file_content, jspf.tree_content)

    def test_tree_content_when_tree_exists(self):
        jspf = OldJournalPageFile(self.html_file("bjmbr_iaboutj"))
        self.assertIn("<html", jspf.tree_content.lower())

    def test_body_tree_without_body_tag(self):
        path = self.write_temp_html(
            "frag",
            "iaboutj.htm",
            "<html><head><title>x</title></head></html>",
        )
        jspf = OldJournalPageFile(path)
        self.assertIsNone(jspf.tree.body)
        self.assertIs(jspf._body_tree, jspf.tree)

    def test_body_content_when_body_tree_is_none(self):
        jspf = OldJournalPageFile(self.html_file("bjmbr_iaboutj"))
        jspf.tree = None
        self.assertIsNone(jspf.body_content)

    def test_get_tree_logs_parser_failures(self):
        no_end = self.write_temp_html(
            "fail",
            "iaboutj.htm",
            "<html><body><table><tr><td>Editable</td></tr></table>"
            "<p>content</p></body></html>",
        )
        jspf = OldJournalPageFile(no_end)
        self.assertIsNone(jspf.middle_end_insertion_position)

        no_begin = self.write_temp_html(
            "fail2",
            "iaboutj.htm",
            "<html><body><table><tr><td>plain</td></tr></table>"
            '<p>content</p><a href="javascript:history.back()">Back</a>'
            "</body></html>",
        )
        jspf2 = OldJournalPageFile(no_begin)
        self.assertIsNotNone(jspf2.middle_end_insertion_position)
        self.assertIsNone(jspf2.middle_begin_insertion_position)

    def test_middle_end_insertion_position_hr_fallback(self):
        path = self.write_temp_html(
            "hr",
            "iaboutj.htm",
            "<html><body><table><tr><td>Editable</td></tr></table>"
            "<p>content</p><hr/></body></html>",
        )
        jspf = OldJournalPageFile(path)
        pos = jspf.middle_end_insertion_position
        self.assertIsNotNone(pos)
        self.assertEqual("hr", pos.name)

    def test_anchor_empty_for_unknown_page(self):
        path = self.write_temp_html(
            "rbep",
            "psubscrp.htm",
            "<html><body><p>subscription</p></body></html>",
        )
        jspf = OldJournalPageFile(path)
        self.assertEqual("", jspf.anchor)

    def test_anchor_title_alt_match(self):
        path = self.write_temp_html(
            "alt",
            "pabout.htm",
            "<html><body><p>about</p></body></html>",
        )
        jspf = OldJournalPageFile(path)
        self.assertEqual("<h1>Sobre o periódico</h1>", jspf.anchor_title)

    def test_anchor_title_empty_when_no_match(self):
        path = self.write_temp_html(
            "alt",
            "isubscrp.htm",
            "<html><body><p>subscription</p></body></html>",
        )
        jspf = OldJournalPageFile(path)
        self.assertEqual("<h1></h1>", jspf.anchor_title)

    def test_unavailable_message_en(self):
        path = self.write_temp_html(
            "en",
            "iaboutj.htm",
            "<html><body><table><tr><td>Editable</td></tr></table>"
            '<p id="middle_begin"></p>'
            "<p>Information is not available in English. "
            "Consult other version.</p>"
            '<p id="middle_end"></p>'
            '<a href="javascript:history.back()">Back</a>'
            "</body></html>",
        )
        jspf = OldJournalPageFile(path)
        self.assertEqual(
            jspf.EN_UNAVAILABLE_MSG,
            jspf._check_unavailable_message("not available in English"),
        )
        self.assertIn(jspf.EN_UNAVAILABLE_MSG, jspf.unavailable_message)

    def test_check_unavailable_message_no_match(self):
        jspf = OldJournalPageFile(self.html_file("bjmbr_iaboutj"))
        self.assertIsNone(jspf._check_unavailable_message("regular content"))

    def test_get_unavailable_message_no_body_match(self):
        jspf = OldJournalPageFile(self.html_file("bjmbr_iaboutj"))
        jspf._get_unavailable_message()
        self.assertIsNone(jspf._unavailable_message)

    def test_get_unavailable_message_long_middle_item(self):
        path = self.write_temp_html(
            "en",
            "iaboutj.htm",
            "<html><body><table><tr><td>Editable</td></tr></table>"
            "<p>Information is not available in English.</p>"
            '<p id="middle_begin"></p>'
            "<p>" + ("x" * 300) + "</p>"
            '<p id="middle_end"></p>'
            '<a href="javascript:history.back()">Back</a>'
            "</body></html>",
        )
        jspf = OldJournalPageFile(path)
        jspf._get_unavailable_message()
        self.assertIsNone(jspf._unavailable_message)

    def test_get_unavailable_message_item_without_msg(self):
        path = self.write_temp_html(
            "en",
            "iaboutj.htm",
            "<html><body><table><tr><td>Editable</td></tr></table>"
            "<p>Information is not available in English.</p>"
            '<p id="middle_begin"></p>'
            "<p>Short unrelated text</p>"
            '<p id="middle_end"></p>'
            '<a href="javascript:history.back()">Back</a>'
            "</body></html>",
        )
        jspf = OldJournalPageFile(path)
        jspf._get_unavailable_message()
        self.assertIsNone(jspf._unavailable_message)

    def test_middle_properties_are_cached(self):
        jspf = OldJournalPageFile(self.html_file("ea_pinstruc"))
        children1 = jspf.middle_children
        children2 = jspf.middle_children
        self.assertIs(children1, children2)
        items1 = jspf.middle_items
        items2 = jspf.middle_items
        self.assertIs(items1, items2)
        text1 = jspf.middle_text
        text2 = jspf.middle_text
        self.assertIs(text1, text2)

    def test_get_alternative_middle_text_without_table(self):
        content = "<p>Plain content only</p>"
        path = self.write_temp_html("alt", "iaboutj.htm", content)
        jspf = OldJournalPageFile(path)
        middle = jspf.get_alternative_middle_text()
        self.assertIn("Plain content only", middle)

    def test_get_middle_children_stops_at_middle_end(self):
        path = self.write_temp_html(
            "stop",
            "iaboutj.htm",
            "<html><body><table><tr><td>Editable</td></tr></table>"
            "<p id='middle_begin'>start</p>"
            "<p>inside</p>"
            "<p id='middle_end'>end</p>"
            "<p>outside</p>"
            '<a href="javascript:history.back()">Back</a>'
            "</body></html>",
        )
        jspf = OldJournalPageFile(path)
        items = jspf.middle_children
        self.assertTrue(any("inside" in str(item) for item in items))
        self.assertFalse(any("outside" in str(item) for item in items))

    def test_get_middle_children_without_markers(self):
        path = self.write_temp_html(
            "nomarkers",
            "iaboutj.htm",
            "<html><body><p>only content</p></body></html>",
        )
        jspf = OldJournalPageFile(path)
        self.assertEqual([], jspf.middle_children)

    def test_wrap_tag_without_direct_string(self):
        soup = BeautifulSoup(
            "<p><b><span>a</span><span>b</span></b></p>", "html.parser"
        )
        nested = soup.find("b")
        self.assertIsNone(nested.string)
        self.assertIsNone(wrap(nested, soup.new_tag("strong")))

    def test_wrap_navigable_string_in_tree(self):
        soup = BeautifulSoup("<p>text</p>", "html.parser")
        text_node = soup.p.string
        wrapped = wrap(text_node, soup.new_tag("em"))
        self.assertEqual("<em>text</em>", str(wrapped))

    def test_wrap_unsupported_child_type(self):
        soup = BeautifulSoup("<p>x</p>", "html.parser")
        self.assertIsNone(wrap(42, soup.new_tag("span")))

    def test_get_alternative_middle_text_home_branch(self):
        content = (
            "<TABLE><tr><td>header</td></tr></TABLE>"
            "<P>Main content here</P><P>Footer</P>Home tail"
        )
        path = self.write_temp_html("alt", "iaboutj.htm", content)
        jspf = OldJournalPageFile(path)
        middle = jspf.get_alternative_middle_text()
        self.assertIn("Main content here", middle)
        self.assertNotIn("Home tail", middle)

    def test_get_alternative_middle_text_volver_branch(self):
        content = (
            "</TABLE><P>Spanish content</P><P>more</P>Volver tail"
        )
        path = self.write_temp_html("alt", "eaboutj.htm", content)
        jspf = OldJournalPageFile(path)
        middle = jspf.get_alternative_middle_text()
        self.assertIn("Spanish content", middle)
        self.assertNotIn("Volver tail", middle)

    def test_get_alternative_middle_text_voltar_branch(self):
        content = "</TABLE><P>Portuguese content</P><P>more</P>Voltar tail"
        path = self.write_temp_html("alt", "paboutj.htm", content)
        jspf = OldJournalPageFile(path)
        middle = jspf.get_alternative_middle_text()
        self.assertIn("Portuguese content", middle)
        self.assertNotIn("Voltar tail", middle)

    def test_get_alternative_middle_text_rodape_branch(self):
        content = (
            "</TABLE><P>Content before rodape</P>"
            '<p class="rodape">footer text</p>'
        )
        path = self.write_temp_html("alt", "paboutj.htm", content)
        jspf = OldJournalPageFile(path)
        middle = jspf.get_alternative_middle_text()
        self.assertIn("Content before rodape", middle)
        self.assertNotIn("footer text", middle)

    def test_get_alternative_middle_text_creativecommons_branch(self):
        content = (
            "</TABLE><P>Licensed content</P><P>more</P>"
            "https://creativecommons.org/licenses/by/4.0/ tail"
        )
        path = self.write_temp_html("alt", "iaboutj.htm", content)
        jspf = OldJournalPageFile(path)
        middle = jspf.get_alternative_middle_text()
        self.assertIn("Licensed content", middle)
        self.assertNotIn("creativecommons.org", middle)

    def test_get_alternative_middle_text_body_and_tag_normalization(self):
        content = (
            "<BODY><TABLE><tr><td>x</td></tr></TABLE>"
            "<P>Normalized</P></BODY>"
        )
        path = self.write_temp_html("alt", "iaboutj.htm", content)
        jspf = OldJournalPageFile(path)
        middle = jspf.get_alternative_middle_text()
        self.assertIn("Normalized", middle)
        self.assertNotIn("</body>", middle.lower())

    def test_middle_uses_alternative_when_no_middle_end(self):
        path = self.write_temp_html(
            "altmid",
            "iaboutj.htm",
            "</TABLE><!-- #BeginEditable \"texto\" -->"
            "<p>Alt middle content</p></body></html>",
        )
        jspf = OldJournalPageFile(path)
        self.assertIsNone(jspf.p_middle_end)
        middle = jspf.middle
        self.assertIn("Alt middle content", middle)

    def test_get_middle_children_skips_comments(self):
        path = self.write_temp_html(
            "comment",
            "iaboutj.htm",
            "<html><body><table><tr><td>Editable</td></tr></table>"
            "<p id='middle_begin'></p><!-- comment -->"
            "<p>inside</p><p id='middle_end'></p></body></html>",
        )
        jspf = OldJournalPageFile(path)
        items = jspf.middle_children
        self.assertTrue(any("inside" in str(item) for item in items))

    def test_insert_middle_markers_when_position_missing(self):
        path = self.write_temp_html(
            "plain",
            "iaboutj.htm",
            "<html><body><p>no markers</p></body></html>",
        )
        jspf = OldJournalPageFile(path)
        self.assertIsNone(jspf.insert_p_middle_begin())
        self.assertIsNone(jspf.insert_p_middle_end())

    def test_find_middle_markers_not_exactly_one(self):
        path = self.write_temp_html(
            "dup",
            "iaboutj.htm",
            "<html><body><table><tr><td>Editable</td></tr></table>"
            "<p id='middle_begin'>a</p><p id='middle_begin'>b</p>"
            "<p id='middle_end'>c</p><p id='middle_end'>d</p>"
            '<a href="javascript:history.back()">Back</a>'
            "</body></html>",
        )
        jspf = OldJournalPageFile(path)
        self.assertIsNone(jspf.find_p_middle_begin())
        self.assertIsNone(jspf.find_p_middle_end())
