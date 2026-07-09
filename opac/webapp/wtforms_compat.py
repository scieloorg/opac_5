# coding: utf-8

import logging

logger = logging.getLogger(__name__)

_PATCHED = False


def _wtforms_major_minor():
    import wtforms

    return tuple(int(part) for part in wtforms.__version__.split(".")[:2])


def iter_choice(val, label, selected):
    """Return a choice tuple compatible with the installed WTForms version."""
    if _wtforms_major_minor() >= (3, 2):
        return val, label, selected, {}
    return val, label, selected


def _patch_iter_choices_method(cls):
    original = cls.iter_choices
    if getattr(original, "_wtforms_compat_patched", False):
        return

    def patched(self):
        for choice in original(self):
            if isinstance(choice, tuple) and len(choice) == 3:
                yield iter_choice(*choice)
            else:
                yield choice

    patched._wtforms_compat_patched = True
    cls.iter_choices = patched


def apply_wtforms_compat():
    """Patch third-party fields that still yield 3-tuples for WTForms 3.2+."""
    global _PATCHED

    if _PATCHED or _wtforms_major_minor() < (3, 2):
        return

    from flask_admin.contrib.sqla import fields as sqla_fields
    from flask_mongoengine.wtf import fields as me_fields

    for cls in (
        sqla_fields.QuerySelectField,
        sqla_fields.QuerySelectMultipleField,
        me_fields.QuerySetSelectField,
    ):
        _patch_iter_choices_method(cls)

    _PATCHED = True
    logger.debug("Applied WTForms 3.2 iter_choices compatibility patches.")
