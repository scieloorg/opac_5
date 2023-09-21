import re
from datetime import datetime
from typing import Generator, List

from exceptions import InvalidOrderValueError
from opac_schema.v1 import models

EMAIL_SPLIT_REGEX = re.compile("[;\\/]+")


def _nestget(data, *path, default=""):
    """Obtém valores de list ou dicionários."""
    for key_or_index in path:
        try:
            data = data[key_or_index]
        except (KeyError, IndexError):
            return default
    return data


def _get_main_article_title(data):
    try:
        lang = _nestget(data, "article", 0, "lang", 0)
        return data["display_format"]["article_title"][lang]
    except KeyError:
        return _nestget(data, "article_meta", 0, "article_title", 0)


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
            for item in metadata.get("institution_responsible_for", [{}])
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
    if journal.logo_url is None or len(journal.logo_url) == 0:
        journal.logo_url = metadata.get("logo_url", "")
    journal.current_status = metadata.get("status_history", [{}])[-1].get("status")

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

    journal.created = data.get("created", "")
    journal.updated = data.get("updated", "")

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

    if issue_order:
        issue.order = issue_order

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
            if metadata.get(name)
        )

    issue.label = _get_issue_label(metadata) or None

    if metadata.get("supplement"):
        issue.suppl_text = metadata.get("supplement")
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

    issue.created = data.get("created", "")
    issue.updated = data.get("updated", "")

    return issue


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

    try:
        article = models.Article.objects.get(_id=document_id)

        if issue_id is None:
            issue_id = article.issue._id
    except models.Article.DoesNotExist:
        article = models.Article()

    # atualiza status
    article.is_public = True

    # Garante que o campo de relacionamento com outro artigo esteja vazio.
    article.related_articles = []

    # Dados principais
    article.title = _get_main_article_title(data)
    article.section = _nestget(data, "article_meta", 0, "pub_subject", 0)
    article.abstract = _nestget(data, "article_meta", 0, "abstract", 0)

    # Identificadores
    article._id = document_id
    article.aid = document_id
    # Lista de SciELO PIDs dentro de article_meta
    scielo_pids = [
        (
            f"v{version}",
            _nestget(
                data, "article_meta", 0, f"scielo_pid_v{version}", 0, default=None
            ),
        )
        for version in range(1, 4)
    ]
    article.scielo_pids = {
        version: value for version, value in scielo_pids if value is not None
    }

    # insere outros tipos de PIDs/IDs em `scielo_ids['other']`
    article_publisher_id = (
        _nestget(data, "article_meta", 0, "article_publisher_id") or []
    )
    repeated_doc_pids = repeated_doc_pids or []
    repeated_doc_pids = list(set(repeated_doc_pids + article_publisher_id))
    if repeated_doc_pids:
        article.scielo_pids.update({"other": repeated_doc_pids})

    article.aop_pid = _nestget(data, "article_meta", 0, "previous_pid", 0)
    article.pid = article.scielo_pids.get("v2")

    article.doi = _nestget(data, "article_meta", 0, "article_doi", 0)

    def _get_article_authors(data) -> Generator:
        """Recupera a lista de autores do artigo"""

        for contrib in _nestget(data, "contrib"):
            if _nestget(contrib, "contrib_type", 0) in AUTHOR_CONTRIB_TYPES:
                yield (
                    "%s%s, %s"
                    % (
                        _nestget(contrib, "contrib_surname", 0),
                        " " + _nestget(contrib, "contrib_suffix", 0)
                        if _nestget(contrib, "contrib_suffix", 0)
                        else "",
                        _nestget(contrib, "contrib_given_names", 0),
                    )
                )

    def _get_author_affiliation(data, xref_aff_id):
        """Recupera a afiliação ``institution_orgname`` de xref_aff_id"""

        for aff in _nestget(data, "aff"):
            if _nestget(aff, "aff_id", 0) == xref_aff_id:
                return _nestget(aff, "institution_orgname", 0)

    def _get_article_authors_meta(data):
        """Recupera a lista de autores do artigo para popular opac_schema.AuthorMeta,
        contendo a afiliação e orcid"""

        authors = []

        for contrib in _nestget(data, "contrib"):
            if _nestget(contrib, "contrib_type", 0) in AUTHOR_CONTRIB_TYPES:
                author_dict = {}

                author_dict["name"] = "%s%s, %s" % (
                    _nestget(contrib, "contrib_surname", 0),
                    " " + _nestget(contrib, "contrib_suffix", 0)
                    if _nestget(contrib, "contrib_suffix", 0)
                    else "",
                    _nestget(contrib, "contrib_given_names", 0),
                )

                if _nestget(contrib, "contrib_orcid", 0):
                    author_dict["orcid"] = _nestget(contrib, "contrib_orcid", 0)

                aff = _get_author_affiliation(data, _nestget(contrib, "xref_aff", 0))

                if aff:
                    author_dict["affiliation"] = aff

                authors.append(models.AuthorMeta(**author_dict))

        return authors

    def _get_original_language(data: dict) -> str:
        return _nestget(data, "article", 0, "lang", 0)

    def _get_languages(data: dict) -> List[str]:
        """Recupera a lista de idiomas em que o artigo foi publicado"""

        translations_type = [
            "translation",
        ]

        languages = [_get_original_language(data)]

        for sub_article in _nestget(data, "sub_article"):
            if _nestget(sub_article, "article", 0, "type", 0) in translations_type:
                languages.append(_nestget(sub_article, "article", 0, "lang", 0))

        return languages

    def _get_translated_titles(data: dict) -> Generator:
        """Recupera a lista de títulos do artigo"""
        try:
            _lang = _get_original_language(data)
            for lang, title in data["display_format"]["article_title"].items():
                if _lang != lang:
                    yield models.TranslatedTitle(
                        **{
                            "name": title,
                            "language": lang,
                        }
                    )
        except KeyError:
            for sub_article in _nestget(data, "sub_article"):
                yield models.TranslatedTitle(
                    **{
                        "name": _nestget(
                            sub_article, "article_meta", 0, "article_title", 0
                        ),
                        "language": _nestget(sub_article, "article", 0, "lang", 0),
                    }
                )

    def _get_translated_sections(data: dict) -> List[models.TranslatedSection]:
        """Recupera a lista de seções traduzidas a partir do document front"""

        translations_type = [
            "translation",
        ]

        sections = [
            models.TranslatedSection(
                **{
                    "name": _nestget(data, "article_meta", 0, "pub_subject", 0),
                    "language": _get_original_language(data),
                }
            )
        ]

        for sub_article in _nestget(data, "sub_article"):
            if _nestget(sub_article, "article", 0, "type", 0) in translations_type:
                sections.append(
                    models.TranslatedSection(
                        **{
                            "name": _nestget(
                                sub_article, "article_meta", 0, "pub_subject", 0
                            ),
                            "language": _nestget(sub_article, "article", 0, "lang", 0),
                        }
                    )
                )

        return sections

    def _get_abstracts(data: dict) -> List[models.Abstract]:
        """Recupera todos os abstracts do artigo"""

        abstracts = []

        # Abstract do texto original
        if len(_nestget(data, "article_meta", 0, "abstract", 0)) > 0:
            abstracts.append(
                models.Abstract(
                    **{
                        "text": _nestget(data, "article_meta", 0, "abstract", 0),
                        "language": _get_original_language(data),
                    }
                )
            )

        # Trans abstracts
        abstracts += [
            models.Abstract(
                **{
                    "text": _nestget(trans_abstract, "text", 0),
                    "language": _nestget(trans_abstract, "lang", 0),
                }
            )
            for trans_abstract in data.get("trans_abstract", [])
            if trans_abstract and _nestget(trans_abstract, "text", 0)
        ]

        # Abstracts de sub-article
        abstracts += [
            models.Abstract(
                **{
                    "text": _nestget(sub_article, "article_meta", 0, "abstract", 0),
                    "language": _nestget(sub_article, "article", 0, "lang", 0),
                }
            )
            for sub_article in _nestget(data, "sub_article")
            if len(_nestget(sub_article, "article_meta", 0, "abstract", 0)) > 0
        ]

        return abstracts

    def _get_keywords(data: dict) -> List[models.ArticleKeyword]:
        """Retorna a lista de palavras chaves do artigo e dos
        seus sub articles"""

        keywords = [
            models.ArticleKeyword(
                **{
                    "keywords": _nestget(kwd_group, "kwd", default=[]),
                    "language": _nestget(kwd_group, "lang", 0),
                }
            )
            for kwd_group in _nestget(data, "kwd_group", default=[])
        ]

        for sub_article in _nestget(data, "sub_article"):
            [
                keywords.append(
                    models.ArticleKeyword(
                        **{
                            "keywords": _nestget(kwd_group, "kwd", default=[]),
                            "language": _nestget(kwd_group, "lang", 0),
                        }
                    )
                )
                for kwd_group in _nestget(sub_article, "kwd_group", default=[])
            ]

        return keywords

    def _get_order(document_order, pid_v2):
        try:
            return int(document_order)
        except (ValueError, TypeError):
            order_err_msg = "'{}' is not a valid value for " "'article.order'".format(
                document_order
            )
            try:
                document_order = int(pid_v2[-5:])
                print(
                    "{}. It was set '{} (the last 5 digits of PID v2)' to "
                    "'article.order'".format(order_err_msg, document_order)
                )
                return document_order
            except (ValueError, TypeError):
                raise InvalidOrderValueError(order_err_msg)

    def _get_publication_date_by_type(
        publication_dates, date_type="pub", reverse_date=True
    ):
        """
        Obtém a lista de datas de publicação do /front do kernel,
        no seguinte formato, exemplo:

        [{'text': ['2022'],
          'pub_type': [],
          'pub_format': ['electronic'],
          'date_type': ['collection'],
          'day': [],
          'month': [],
          'year': ['2022'],
          'season': []},
        {'text': ['02 02 2022'],
         'pub_type': [],
         'pub_format': ['electronic'],
         'date_type': ['pub'],
         'day': ['02'],
         'month': ['02'],
         'year': ['2022'],
         'season': []}]

         Retorna a data considerando a chave o tipo `date_type`.

         Return a string.
        """

        def _check_date_format(date_string, format="%Y-%m-%d"):
            """
            Check if date as string is a expected format.
            """
            try:
                return datetime.strptime(date_string, format).strftime(format)
            except ValueError:
                print("The date isnt in a well format, the correct format: %s" % format)

            return date_string

        try:
            formed_date = ""
            for pubdate in publication_dates or []:
                if date_type in pubdate.get("date_type") or "epub" in pubdate.get(
                    "pub_type"
                ):
                    pubdate_list = [
                        _nestget(pubdate, "day", 0),
                        _nestget(pubdate, "month", 0),
                        _nestget(pubdate, "year", 0),
                    ]
                    if reverse_date:
                        pubdate_list.reverse()
                    formed_date = "-".join([pub for pub in pubdate_list if pub])
            return (
                _check_date_format(formed_date)
                if reverse_date
                else _check_date_format(formed_date, "%d-%m-%Y")
            )
        except (IndexError, AttributeError):
            print(
                "Missing publication date type: {} in list of dates: {}".format(
                    date_type, publication_dates
                )
            )

    article.authors = list(_get_article_authors(data))
    article.authors_meta = _get_article_authors_meta(data)
    article.languages = list(_get_languages(data))
    article.translated_titles = list(_get_translated_titles(data))
    article.sections = list(_get_translated_sections(data))
    article.abstracts = list(_get_abstracts(data))
    article.keywords = list(_get_keywords(data))

    article.abstract_languages = [
        abstract["language"] for abstract in article.abstracts
    ]

    article.original_language = _get_original_language(data)
    publications_date = _nestget(data, "pub_date")

    if publications_date:
        formed_publication_date = _get_publication_date_by_type(
            publications_date, "pub"
        )
        article.publication_date = formed_publication_date

    article.type = _nestget(data, "article", 0, "type", 0)

    # Dados de localização
    article.elocation = _nestget(data, "article_meta", 0, "pub_elocation", 0)
    article.fpage = _nestget(data, "article_meta", 0, "pub_fpage", 0)
    article.fpage_sequence = _nestget(data, "article_meta", 0, "pub_fpage_seq", 0)
    article.lpage = _nestget(data, "article_meta", 0, "pub_lpage", 0)

    if article.issue is not None and article.issue.number == "ahead":
        if article.aop_url_segs is None:
            url_segs = {
                "url_seg_article": article.url_segment,
                "url_seg_issue": article.issue.url_segment,
            }
            article.aop_url_segs = models.AOPUrlSegments(**url_segs)

    # Issue vinculada
    issue = models.Issue.objects.get(_id=issue_id)
    issue.is_public = True

    print("ISSUE %s" % str(issue))
    print("ARTICLE.ISSUE %s" % str(article.issue))
    print("ARTICLE.AOP_PID %s" % str(article.aop_pid))
    print("ARTICLE.PID %s" % str(article.pid))

    article.issue = issue
    article.journal = issue.journal
    article.order = _get_order(document_order, article.pid)
    article.xml = document_xml_url

    # Campo de compatibilidade do OPAC
    article.htmls = [{"lang": lang} for lang in _get_languages(data)]

    article.created = article.created or datetime.utcnow().isoformat()
    article.updated = datetime.utcnow().isoformat()

    return article
