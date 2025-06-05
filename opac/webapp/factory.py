import logging
import re
from datetime import datetime

from exceptions import PublishDocumentError
from opac_schema.v1 import models

EMAIL_SPLIT_REGEX = re.compile("[;\\/]+")


def isoformat_to_datetime(date_):
    if not date_:
        return datetime.utcnow().isoformat()
    return datetime.fromisoformat(date_)


def JournalFactory(data):
    """Produz instância de `models.Journal` a partir dos dados retornados do
    endpoint `/journals/:journal_id` do Kernel.
    """
    metadata = data

    try:
        journal = models.Journal.objects.get(_id=data.get("id"))
    except models.Journal.DoesNotExist:
        journal = models.Journal()

    journal._id = journal.jid = data.get("id")
    journal.title = metadata.get("title", "")
    journal.title_iso = metadata.get("title_iso", "")
    journal.short_title = metadata.get("short_title", "")
    journal.acronym = metadata.get("acronym", "")
    journal.scielo_issn = metadata.get("scielo_issn", "")
    journal.print_issn = metadata.get("print_issn", "")
    journal.eletronic_issn = metadata.get("electronic_issn", "")

    # Subject Categories
    journal.subject_categories = metadata.get("subject_categories", [])

    # Métricas
    journal.metrics = models.JounalMetrics(**metadata.get("metrics", {}))

    # Issue count
    journal.issue_count = len(data.get("items", []))

    # Mission
    journal.mission = [
        models.Mission(**{"language": m["language"], "description": m["value"]})
        for m in metadata.get("mission", [])
    ]

    # Study Area
    journal.study_areas = metadata.get("subject_areas", [])

    # Sponsors
    sponsors = metadata.get("sponsors", [])
    journal.sponsors = [s["name"] for s in sponsors if sponsors]

    # TODO: Verificar se esse e-mail é o que deve ser colocado no editor.
    # Editor mail
    if metadata.get("contact", ""):
        contact = metadata.get("contact")
        journal.editor_email = EMAIL_SPLIT_REGEX.split(contact.get("email", ""))[
            0
        ].strip()
        journal.publisher_address = contact.get("address")

    if metadata.get("institution_responsible_for"):
        institutions = [
            item
            for item in metadata.get("institution_responsible_for") or [{}]
            if item.get("name")
        ]
        if institutions:
            journal.publisher_name = ", ".join(
                item.get("name") for item in institutions
            )
            institution = institutions[0]
            journal.publisher_city = institution.get("city")
            journal.publisher_state = institution.get("state")
            journal.publisher_country = institution.get("country")

    journal.online_submission_url = metadata.get("online_submission_url", "")

    if "missing" in journal.logo_url or not journal.logo_url:
        journal.logo_url = metadata.get("logo_url")
    journal.current_status = metadata.get("current_status")

    timelines = []
    for timeline in metadata.get("status_history", []):
        timelines.append(
            models.Timeline(
                **{
                    "status": timeline.get("status", ""),
                    "since": timeline.get("date", ""),
                    "reason": timeline.get("reason", ""),
                }
            )
        )

    journal.timeline = timelines

    if metadata.get("next_journal", ""):
        journal.next_title = metadata["next_journal"]["name"]

    if metadata.get("previous_journal", ""):
        journal.previous_journal_ref = metadata["previous_journal"]["name"]

    journal.created = journal.created or isoformat_to_datetime(data.get("created"))
    journal.updated = isoformat_to_datetime(data.get("updated"))
    journal.is_public = metadata["is_public"]
    journal.old_information_page = metadata.get("old_information_page")

    return journal


def IssueFactory(data, journal_id, issue_order=None, _type="regular"):
    """
    Realiza o registro fascículo utilizando o opac schema.

    Esta função pode lançar a exceção `models.Journal.DoesNotExist`.

    Para satisfazer a obrigatoriedade do ano para os "Fascículos" ahead,
    estamos fixando o ano de fascículos do tipo ``ahead`` com o valor 9999
    """

    metadata = data

    try:
        issue = models.Issue.objects.get(_id=data["id"])
    except models.Issue.DoesNotExist:
        issue = models.Issue()
    else:
        journal_id = journal_id or issue.journal._id

    _type = (data["id"].endswith("-aop") and "ahead") or _type

    issue._id = issue.iid = data["id"]
    issue.spe_text = metadata.get("spe_text", "")
    issue.start_month = metadata.get("publication_months", {"range": [0, 0]}).get(
        "range", [0]
    )[0]
    issue.end_month = metadata.get("publication_months", {"range": [0, 0]}).get(
        "range", [0]
    )[-1]

    if _type == "ahead":
        issue.year = issue.year or "9999"
        issue.number = issue.number or "ahead"
    else:
        issue.year = metadata.get("publication_year", issue.year)
        issue.number = metadata.get("number", issue.number)

    issue.volume = metadata.get("volume", "")

    if not issue_order and data.get("pid"):
        issue_order = data.get("order") or data.get("pid")[-4:]
    try:
        issue.order = int(issue_order)
    except (ValueError, TypeError):
        pass

    issue.pid = metadata.get("pid", "")
    issue.journal = models.Journal.objects.get(_id=journal_id)

    def _get_issue_label(metadata: dict) -> str:
        """Produz o label esperado pelo OPAC de acordo com as regras aplicadas
        pelo OPAC Proc e Xylose.

        Args:
            metadata (dict): conteúdo de um bundle

        Returns:
            str: label produzido a partir de um bundle
        """
        prefixes = ("v", "n", "s")
        names = ("volume", "number", "supplement")
        return "".join(
            f"{prefix}{metadata.get(name)}"
            for prefix, name in zip(prefixes, names)
            if metadata.get(name) is not None
        )

    issue.suppl_text = metadata.get("supplement")
    issue.label = _get_issue_label(metadata) or None
    issue.type = metadata.get("type")

    if not issue.type:
        if metadata.get("supplement"):
            issue.type = "supplement"
        elif issue.volume and not issue.number:
            issue.type = "volume_issue"
        elif issue.number and "spe" in issue.number:
            issue.type = "special"
        elif _type == "ahead" and not data.get("items"):
            """
            Caso não haja nenhum artigo no bundle de ahead, ele é definido como
            ``outdated_ahead``, para que não apareça na grade de fascículos
            """
            issue.type = "outdated_ahead"
        else:
            issue.type = _type

    issue.created = issue.created or isoformat_to_datetime(data.get("created"))
    issue.updated = isoformat_to_datetime(data.get("updated"))

    return issue


class AuxiliarArticleFactory:
    # https://github.com/scieloorg/opac-airflow/blob/4103e6cab318b737dff66435650bc4aa0c794519/airflow/dags/operations/sync_kernel_to_website_operations.py#L82

    def __init__(self, doc_id, issue_id=None):
        try:
            self.doc = models.Article.objects.get(_id=doc_id)
        except models.Article.DoesNotExist:
            self.doc = models.Article()

        if not self.doc.issue and issue_id:
            self.doc.issue = models.Issue.objects.get(_id=issue_id)

        self.doc.journal = self.doc.issue.journal

        self.doc._id = doc_id
        self.doc.aid = doc_id

        # Garante que o campo de relacionamento esteja vazio
        self.doc.authors_meta = None
        self.doc.authors = None
        self.doc.translated_titles = None
        self.doc.sections = None
        self.doc.abstract = None
        self.doc.abstracts = None
        self.doc.abstract_languages = None
        self.doc.keywords = None
        self.doc.doi_with_lang = None
        self.doc.related_articles = None
        self.doc.htmls = None
        self.doc.pdfs = None
        self.doc.mat_suppl_items = None
        self.doc.collabs = None

    def add_identifiers(self, v2, aop_pid, other_pids=None):
        # Identificadores
        self.doc.pid = v2

        self.doc.scielo_pids = self.doc.scielo_pids or {}
        self.doc.scielo_pids["v2"] = v2
        self.doc.scielo_pids["v3"] = self.doc._id

        if other_pids:
            for item in other_pids:
                self.add_other_pid(item)

        if aop_pid:
            self.doc.aop_pid = aop_pid

    def add_other_pid(self, other_pid):
        if other_pid:
            self.doc.scielo_pids.setdefault("other", [])
            if other_pid not in self.doc.scielo_pids["other"]:
                self.doc.scielo_pids["other"].append(other_pid)

    def add_journal(self, journal):
        if isinstance(journal, models.Journal):
            self.doc.journal = journal
        else:
            self.doc.journal = models.Journal.objects.get(_id=journal)

    def add_issue(self, issue):
        if isinstance(issue, models.Issue):
            self.doc.issue = issue
        else:
            self.doc.issue = models.Issue.objects.get(_id=issue)

    def add_main_metadata(self, title, section, abstract, lang, doi):
        # Dados principais (versão considerada principal)
        # devem conter estilos html (math, italic, sup, sub)
        self.doc.title = title
        self.doc.section = section
        self.doc.abstract = abstract
        self.doc.original_language = lang
        self.doc.doi = doi

    def add_document_type(self, document_type):
        self.doc.type = document_type

    def add_publication_date(self, publication_date):
        self.doc.publication_date = publication_date

    def add_in_issue(
        self, order, fpage=None, fpage_seq=None, lpage=None, elocation=None
    ):
        # Dados de localização no issue
        self.doc.order = order
        self.doc.elocation = elocation
        self.doc.fpage = fpage
        self.doc.fpage_sequence = fpage_seq
        self.doc.lpage = lpage

    def add_author(self, surname, given_names, suffix, affiliation, orcid):
        # author meta
        # authors_meta = EmbeddedDocumentListField(AuthorMeta))
        if self.doc.authors_meta is None:
            self.doc.authors_meta = []
        author = models.AuthorMeta()
        author.surname = surname
        author.given_names = given_names
        author.suffix = suffix
        author.affiliation = affiliation
        author.orcid = orcid
        self.doc.authors_meta.append(author)

        # author
        if self.doc.authors is None:
            self.doc.authors = []
        _author = _format_author_name(
            surname,
            given_names,
            suffix,
        )
        self.doc.authors.append(_author)

    def add_translated_title(self, language, name):
        # translated_titles = EmbeddedDocumentListField(TranslatedTitle))
        if self.doc.translated_titles is None:
            self.doc.translated_titles = []
        _translated_title = models.TranslatedTitle()
        _translated_title.name = name
        _translated_title.language = language
        self.doc.translated_titles.append(_translated_title)

    def add_section(self, language, name):
        # sections = EmbeddedDocumentListField(TranslatedSection))
        if self.doc.sections is None:
            self.doc.sections = []
        _translated_section = models.TranslatedSection()
        _translated_section.name = name
        _translated_section.language = language
        self.doc.sections.append(_translated_section)

    def add_abstract(self, language, text):
        # abstracts = EmbeddedDocumentListField(Abstract))
        if self.doc.abstracts is None:
            self.doc.abstracts = []
        if self.doc.abstract_languages is None:
            self.doc.abstract_languages = []
        _abstract = models.Abstract()
        _abstract.text = text
        _abstract.language = language
        self.doc.abstracts.append(_abstract)
        self.doc.abstract_languages.append(language)

    def add_keywords(self, language, keywords):
        # kwd_groups = EmbeddedDocumentListField(ArticleKeyword))
        if self.doc.keywords is None:
            self.doc.keywords = []
        _kwd_group = models.ArticleKeyword()
        _kwd_group.language = language
        _kwd_group.keywords = keywords
        self.doc.keywords.append(_kwd_group)

    def add_doi_with_lang(self, language, doi):
        # doi_with_lang = EmbeddedDocumentListField(DOIWithLang))
        if self.doc.doi_with_lang is None:
            self.doc.doi_with_lang = []
        _doi_with_lang_item = models.DOIWithLang()
        _doi_with_lang_item.doi = doi
        _doi_with_lang_item.language = language
        self.doc.doi_with_lang.append(_doi_with_lang_item)

    def add_related_article(self, doi, ref_id, related_type, href):
        # related_article = EmbeddedDocumentListField(RelatedArticle))
        if self.doc.related_articles is None:
            self.doc.related_articles = []
        _related_article = models.RelatedArticle()
        _related_article.doi = doi
        _related_article.ref_id = ref_id
        _related_article.related_type = related_type
        _related_article.href = href
        self.doc.related_articles.append(_related_article)

    def add_xml(self, xml):
        self.doc.xml = xml

    def add_html(self, language, uri):
        # htmls = ListField(field=DictField()))
        if self.doc.htmls is None:
            self.doc.htmls = []
        self.doc.htmls.append({"lang": language, "uri": uri})
        self.doc.languages = [html["lang"] for html in self.doc.htmls]

    def add_pdf(self, lang, url, filename, type, classic_uri=None):
        # pdfs = ListField(field=DictField()))
        """
        {
            "lang": rendition["lang"],
            "url": rendition["url"],
            "filename": rendition["filename"],
            "type": "pdf",
        }
        """
        if self.doc.pdfs is None:
            self.doc.pdfs = []
        self.doc.pdfs.append(
            dict(
                lang=lang,
                url=url,
                filename=filename,
                type=type,
                classic_uri=classic_uri,
            )
        )

    def add_mat_suppl(self, lang, url, ref_id, filename):
        # mat_suppl = EmbeddedDocumentListField(MatSuppl))
        if self.doc.mat_suppl_items is None:
            self.doc.mat_suppl_items = []
        _mat_suppl_item = models.MatSuppl()
        _mat_suppl_item.url = url
        _mat_suppl_item.lang = lang
        _mat_suppl_item.ref_id = ref_id
        _mat_suppl_item.filename = filename
        self.doc.mat_suppl_items.append(_mat_suppl_item)

    def publish_document(self, created, updated, is_public):
        """
        Publishes doc data

        Raises
        ------
        DocumentSaveError

        Returns
        -------
        opac_schema.v1.models.Article
        """
        try:
            if self.doc.issue and self.doc.issue.number == "ahead":
                url_segs = {
                    "url_seg_article": self.doc.url_segment,
                    "url_seg_issue": self.doc.issue.url_segment,
                }
                self.doc.aop_url_segs = models.AOPUrlSegments(**url_segs)

            # atualiza status
            self.doc.is_public = is_public
            self.doc.created = self.doc.created or isoformat_to_datetime(created)
            self.doc.updated = isoformat_to_datetime(updated)
            self.doc.save()

            # publica ou despublica o issue à condição de haver ou não artigos publicados
            for item in models.Article.objects.filter(issue=self.doc.issue, is_public=True):
                issue_is_public = True
                break
            else:
                issue_is_public = False

            if issue_is_public != self.doc.issue.is_public:
                self.doc.issue.is_public = issue_is_public
                self.doc.issue.save()

        except Exception as e:
            raise PublishDocumentError(e)
        return self.doc

    def add_collab(self, name):
        # collabs = EmbeddedDocumentListField(Collab)
        if self.doc.collabs is None:
            self.doc.collabs = []
        _collab = models.Collab()
        _collab.name = name
        self.doc.collabs.append(_collab)


def ArticleFactory(
    document_id: str,
    data: dict,
    issue_id: str,
    document_order: int,
    document_xml_url: str,
    repeated_doc_pids=None,
) -> models.Article:
    """Cria uma instância de artigo a partir dos dados de entrada.

    Os dados do parâmetro `data` são adaptados ao formato exigido pelo
    modelo Article do OPAC Schema.

    Args:
        document_id (str): Identificador do documento
        data (dict): Estrutura contendo o `front` do documento.
        issue_id (str): Identificador de issue.
        document_order (int): Posição do artigo.
        document_xml_url (str): URL do XML do artigo
        repeated_doc_pids (str list): Lista de PIDs

    Returns:
        models.Article: Instância de um artigo próprio do modelo de dados do
            OPAC.
    """
    AUTHOR_CONTRIB_TYPES = (
        "author",
        "autor",
    )

    factory = AuxiliarArticleFactory(document_id, issue_id)

    article = factory.doc

    # Dados principais
    factory.add_main_metadata(
        title=data.get("title"),
        section=data.get("section"),
        abstract=data.get("abstract"),
        lang=data.get("lang"),
        doi=data.get("doi")
    )

    factory.add_identifiers(
        v2=data.get("scielo_pids_v2"),
        aop_pid=data.get("aop_pid"),
        other_pids=data.get("other_pids"),
    )

    for item in data.get("authors_meta") or []:
        factory.add_author(
            surname=item.get("surname"),
            given_names=item.get("given_names"),
            suffix=item.get("suffix"),
            affiliation=item.get("affiliation"),
            orcid=item.get("orcid"),
        )

    for item in data.get("htmls") or []:
        factory.add_html(language=item["lang"], uri=item["uri"])

    for item in data.get("pdfs") or []:
        factory.add_pdf(
            lang=item["lang"], url=item["url"],
            filename=item["filename"], type=item["type"],
            classic_uri=item.get("classic_uri"))

    for item in data.get("translated_titles") or []:
        factory.add_translated_title(
            language=item["language"], name=item["name"],
        )

    for item in data.get("translated_sections") or []:
        factory.add_section(
            language=item["language"], name=item["name"],
        )

    for item in data.get("abstracts") or []:
        factory.add_abstract(
            language=item["language"], text=item["text"],
        )

    for item in data.get("keywords") or []:
        factory.add_keywords(
            language=item["language"], keywords=item["keywords"],
        )

    factory.add_publication_date(data.get("publication_date"))

    factory.add_document_type(data.get("type"))

    factory.add_in_issue(
        order=data.get("order"),
        fpage=data.get("fpage"),
        fpage_seq=data.get("fpage_sequence"),
        lpage=data.get("lpage"),
        elocation=data.get("elocation")
    )

    for item in data.get("mat_suppl_items") or []:
        factory.add_mat_suppl(
            lang=item["lang"], url=item["url"],
            ref_id=item["ref_id"], filename=item["filename"],
        )

    factory.add_xml(data.get("xml"))

    for item in data.get("doi_with_lang") or []:
        factory.add_doi_with_lang(
            language=item.get("language"),
            doi=item.get("doi")
        )

    for item in data.get("related_articles") or []:
        factory.add_related_article(
            doi=item.get("doi"), 
            ref_id=item.get("ref_id"), 
            related_type=item.get("related_type"),
            href=item.get("href")
        )

    factory.publish_document(data.get("created"), data.get("updated"), data.get("is_public"))
    
    for item in data.get("collab") or []:
        factory.add_collab(
            name=item.get("name")
        )

    return article


def _format_author_name(surname, given_names, suffix):
    # like airflow
    if suffix:
        suffix = " " + suffix
    return "%s%s, %s" % (surname, suffix or "", given_names)
