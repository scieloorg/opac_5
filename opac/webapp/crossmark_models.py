# coding: utf-8

"""
Modelos MongoEngine para dados de política de atualização (Crossmark) dos periódicos.
"""

from datetime import datetime, timezone

from mongoengine import (
    BooleanField,
    CASCADE,
    DateTimeField,
    Document,
    ReferenceField,
    StringField,
)
from opac_schema.v1.models import Journal


class CrossmarkPage(Document):
    doi = StringField(required=True, unique=True)
    is_doi_active = BooleanField(required=True, default=True)
    language = StringField(max_length=5, required=True)
    journal = ReferenceField(Journal, reverse_delete_rule=CASCADE, required=True)
    created_at = DateTimeField()
    updated_at = DateTimeField()

    meta = {
        "collection": "crossmark_page",
        "indexes": ["doi", "journal"],
    }

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        return super(CrossmarkPage, self).save(*args, **kwargs)
