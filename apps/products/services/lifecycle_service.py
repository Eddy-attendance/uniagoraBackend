"""
apps/products/services/lifecycle_service.py

Centralizes every `ProductStatus` transition (DDS §9.4). Views/serializers
never set `status` directly — every transition funnels through here, matching
the "Template Method-ish lifecycle service" pattern named in Architecture §6.
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import ConflictError

from ..models import Product, ProductStatus


class ProductLifecycleService:
    @staticmethod
    @transaction.atomic
    def renew(*, product):
        """EXPIRED -> ACTIVE only (DDS §9.4). Rejected from
        HIDDEN_BY_SUSPENSION or REMOVED_BY_ADMIN. Resets `expires_at` to
        `now() + 30 days`.
        """
        if product.status != ProductStatus.EXPIRED:
            raise ConflictError("Only expired listings can be renewed.")
        product.status = ProductStatus.ACTIVE
        product.expires_at = timezone.now() + timedelta(days=Product.EXPIRY_DAYS)
        product.save(update_fields=["status", "expires_at", "updated_at"])
        return product

    @staticmethod
    @transaction.atomic
    def admin_remove(*, product):
        """* -> REMOVED_BY_ADMIN. Terminal in MVP — no restoration path is
        invented (DDS §9.4, instruction §12).
        """
        if product.status == ProductStatus.REMOVED_BY_ADMIN:
            raise ConflictError("This listing has already been removed.")
        product.status = ProductStatus.REMOVED_BY_ADMIN
        product.save(update_fields=["status", "updated_at"])
        return product

    @staticmethod
    @transaction.atomic
    def sweep_expire():
        """DDS §7.3/§13: `expires_at <= now() AND status = ACTIVE -> EXPIRED`.
        A single bulk `.update()`. No scheduler infrastructure is introduced
        here (instruction §13) — this is the operation a future scheduled job
        (management command / Celery beat task) would call.
        """
        now = timezone.now()
        return (
            Product.objects.alive()
            .filter(status=ProductStatus.ACTIVE, expires_at__lte=now)
            .update(status=ProductStatus.EXPIRED, updated_at=now)
        )

    # -- Vendor-suspension cascade (DDS §9.2) --------------------------------
    # `products` does not depend on `vendors` (DDS §3) — these operate on
    # `Store` (an existing `products` dependency), not `VendorProfile`. They
    # are written and ready for `vendors.VendorSuspensionService` to call into
    # via a deferred (function-body) import, mirroring the integration pattern
    # already established for `stores`
    # (see apps/vendors/STORE_INTEGRATION_PATCH.md). Wiring the actual call
    # site into apps/vendors/services.py is out of scope for this app per the
    # task brief — flagged in the implementation report, consistent with
    # vendors_EDD.md Assumption 2's own TODO marker.

    @staticmethod
    @transaction.atomic
    def suspend_store_products(*, store):
        """ACTIVE -> HIDDEN_BY_SUSPENSION for every product of a suspended
        vendor's store.
        """
        now = timezone.now()
        Product.objects.alive().filter(store=store, status=ProductStatus.ACTIVE).update(
            status=ProductStatus.HIDDEN_BY_SUSPENSION, updated_at=now
        )

    @staticmethod
    @transaction.atomic
    def reinstate_store_products(*, store):
        """HIDDEN_BY_SUSPENSION -> ACTIVE, except any product whose
        `expires_at` has passed while hidden, which becomes EXPIRED instead
        (DDS §9.2).
        """
        now = timezone.now()
        Product.objects.alive().filter(
            store=store,
            status=ProductStatus.HIDDEN_BY_SUSPENSION,
            expires_at__lte=now,
        ).update(status=ProductStatus.EXPIRED, updated_at=now)
        Product.objects.alive().filter(
            store=store,
            status=ProductStatus.HIDDEN_BY_SUSPENSION,
            expires_at__gt=now,
        ).update(status=ProductStatus.ACTIVE, updated_at=now)
