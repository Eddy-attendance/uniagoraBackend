from django.db import models

from apps.common.managers import SoftDeleteQuerySet


class CategoryQuerySet(SoftDeleteQuerySet):
    def visible(self):
        """Alive, active categories — the customer-facing browse/filter shape."""
        return self.alive().filter(is_active=True)


class CategoryManager(models.Manager.from_queryset(CategoryQuerySet)):
    """Built via the same `Manager.from_queryset()` mechanism `common`
    itself uses (common app EDD §22.1)."""

    pass
