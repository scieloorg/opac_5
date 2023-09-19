import re
from opac_schema.v1 import models


EMAIL_SPLIT_REGEX = re.compile("[;\\/]+")


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


