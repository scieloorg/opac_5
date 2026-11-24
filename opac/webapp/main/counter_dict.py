"""
Funções auxiliares da versão 2 do endpoint counter_dict (/api/v2/counter_dict).
"""
from datetime import datetime, timedelta, timezone


def parse_datetime(value):
    """
    Converte `value` (ISO 8601, conforme `datetime.fromisoformat`) em datetime
    naive. Datas com fuso horário são convertidas para UTC.
    """
    try:
        value = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(value)
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def ceil_to_milliseconds(value):
    """
    MongoDB armazena datas com precisão de milissegundos e o pymongo trunca os
    microssegundos das consultas. Arredonda `value` para cima, ao milissegundo
    seguinte, para que `updated >= value` respeite os microssegundos.
    """
    remainder = value.microsecond % 1000
    if remainder:
        value += timedelta(microseconds=1000 - remainder)
    return value


def isoformat_microseconds(value):
    # datas vindas do MongoDB têm precisão de milissegundos: os 3 últimos
    # dígitos dos microssegundos são sempre 0
    if isinstance(value, datetime):
        return value.isoformat(timespec="microseconds")
    return value


def get_article_data(article):
    return {
        "aid": article.aid,
        "journal_acronym": article.journal.acronym,
        "pid": article.pid if article.pid else "",
        "aop_pid": article.aop_pid if article.aop_pid else "",
        "pid_v1": article.scielo_pids.get("v1", ""),
        "pid_v2": article.scielo_pids.get("v2", ""),
        "pid_v3": article.scielo_pids.get("v3", ""),
        "publication_date": article.publication_date,
        "default_language": article.original_language,
        "is_public": article.is_public,
        "created": isoformat_microseconds(article.created),
        "updated": isoformat_microseconds(article.updated),
    }
