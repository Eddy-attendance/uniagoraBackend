from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import ConflictError

from ..models import Product, ProductStatus


class ProductLifecycleService:
    @staticmethod
    @transaction.atomic
    def renew(*, product):
        """EXPIRED -> ACTIVE only. Rejected from
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
        if product.status == ProductStatus.REMOVED_BY_ADMIN:
            raise ConflictError("This listing has already been removed.")
        product.status = ProductStatus.REMOVED_BY_ADMIN
        product.save(update_fields=["status", "updated_at"])
        return product

    @staticmethod
    @transaction.atomic
    def sweep_expire():
        now = timezone.now()
        return (
            Product.objects.alive()
            .filter(status=ProductStatus.ACTIVE, expires_at__lte=now)
            .update(status=ProductStatus.EXPIRED, updated_at=now)
        )

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
