from django.db import models


class SoftDeleteQuerySet(models.QuerySet):
    """Queryset supporting explicit soft-delete-aware filtering and a genuine hard-delete escape hatch."""

    def alive(self) -> "SoftDeleteQuerySet":
        """Rows not soft-deleted. Call explicitly wherever soft-deleted rows must be excluded."""
        return self.filter(is_deleted=False)

    def dead(self) -> "SoftDeleteQuerySet":
        """Only soft-deleted rows (e.g. admin "recently removed" views, audit queries)."""
        return self.filter(is_deleted=True)

    def delete(self):
        return self.update(is_deleted=True)

    def hard_delete(self):
        return super().delete()


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    pass
