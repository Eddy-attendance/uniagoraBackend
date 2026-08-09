"""
apps/products/managers.py

Repository-lite query-shape centralization for `Product` only (instruction §20).
`ProductImage` / `ProductCategory` need no manager beyond what `BaseModel`'s
inherited `SoftDeleteManager` (`.alive()` / `.dead()`) already provides — no
DDS-named query shape exists for either beyond that, mirroring the precedent
already set by `vendors`/`stores` ("no managers.py beyond what's DDS-named").
"""

from django.db import models

from apps.common.managers import SoftDeleteQuerySet


class ProductQuerySet(SoftDeleteQuerySet):
    def visible(self):
        """Alive + ACTIVE — the base queryset for the primary customer
        marketplace browse/search query (DDS §11: 'Browse products (default
        marketplace view)': `filter(university=u, status=ACTIVE)`).

        Deferred import of ProductStatus avoids a circular import, since
        models.py imports ProductManager (built from this queryset) at
        module load time.
        """
        from .models import ProductStatus

        return self.alive().filter(status=ProductStatus.ACTIVE)

    def for_university(self, university):
        """DDS §11 query-pattern helper. Composable with `.visible()`:
        `Product.objects.visible().for_university(u)`. Does not impose status
        filtering on its own, so it remains useful for admin/vendor contexts
        that need every status for a given university.
        """
        return self.filter(university=university)


class ProductManager(models.Manager.from_queryset(ProductQuerySet)):
    """Built via the same `Manager.from_queryset()` mechanism `common` itself
    establishes (common EDD §22.1) and `universities`/`users` already reuse.
    `objects` remains unfiltered by default (ADR-001) — `.alive()`/`.visible()`
    are always explicit, visible calls.
    """

    pass
