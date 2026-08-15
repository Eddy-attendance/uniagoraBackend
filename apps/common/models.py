"""
Abstract base model shared by every persisted entity in the backend.
"""

import uuid

from django.db import models

from .managers import SoftDeleteManager


class BaseModel(models.Model):
    """
    Supplies the four persistence conventions
    (model-spec preamble): UUID primary key, `created_at`/`updated_at`
    timestamps, and the `is_deleted` soft-delete flag. These four fields
    are deliberately "not repeated in the field tables" of any domain
    model, because they live here once.

    DDS-mandated fields:
        id: UUIDField, primary_key=True, default=uuid4, editable=False.
        created_at: DateTimeField, auto_now_add=True.
        updated_at: DateTimeField, auto_now=True.
        is_deleted: BooleanField, default=False, indexed.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    objects = SoftDeleteManager()

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def delete(self, using=None, keep_parents=False, hard=False):
        """
        Soft-deletes by default is the default deletion behavior application-wide").

        Pass `hard=True` only for the specific, individually-justified
        hard-delete paths
        """
        if hard:
            return super().delete(using=using, keep_parents=keep_parents)
        self.is_deleted = True
        self.save(update_fields=["is_deleted", "updated_at"])
        return None

    def restore(self) -> None:
        """Reverses a soft-delete."""
        self.is_deleted = False
        self.save(update_fields=["is_deleted", "updated_at"])
