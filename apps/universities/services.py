from django.db import transaction

from apps.common.exceptions import ConflictError

from .models import University

_UNSET = object()


class UniversityService:
    """Thin admin-CRUD service layer for `University`."""

    @staticmethod
    @transaction.atomic
    def create(*, name, short_name, logo=None):
        return University.objects.create(name=name, short_name=short_name, logo=logo)

    @staticmethod
    @transaction.atomic
    def update(*, university, name=_UNSET, short_name=_UNSET, logo=_UNSET):
        if name is not _UNSET:
            university.name = name
        if short_name is not _UNSET:
            university.short_name = short_name
        if logo is not _UNSET:
            university.logo = logo
        university.save()
        return university

    @staticmethod
    @transaction.atomic
    def activate(*, university):
        if university.is_active:
            raise ConflictError("University is already active.")
        university.is_active = True
        university.save(update_fields=["is_active", "updated_at"])
        return university

    @staticmethod
    @transaction.atomic
    def deactivate(*, university):
        if not university.is_active:
            raise ConflictError("University is already inactive.")
        university.is_active = False
        university.save(update_fields=["is_active", "updated_at"])
        return university
