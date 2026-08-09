"""
apps/products/services/inventory_service.py

Quantity is the sole inventory source of truth (DDS §7.3, "Out-of-stock
auto-transition"). No method here ever mutates `Product.status` — availability
is a derived property (`Product.is_out_of_stock`), not a lifecycle transition.
Lifecycle transitions belong exclusively to `ProductLifecycleService`.
"""

from django.db import transaction

from apps.common.exceptions import ApplicationError, ConflictError

from ..models import Product


class InventoryService:
    @staticmethod
    @transaction.atomic
    def set_quantity(*, product, quantity):
        """Sets quantity to an absolute value. `status` is never touched —
        an ACTIVE product with quantity 0 remains ACTIVE (and simultaneously
        out of stock, per DDS §5).
        """
        if quantity < 0:
            raise ApplicationError("Quantity cannot be negative.")
        product.quantity = quantity
        product.save(update_fields=["quantity", "updated_at"])
        return product

    @staticmethod
    @transaction.atomic
    def increase_quantity(*, product, amount):
        if amount <= 0:
            raise ApplicationError("Amount must be a positive integer.")
        locked = Product.objects.select_for_update().get(pk=product.pk)
        locked.quantity += amount
        locked.save(update_fields=["quantity", "updated_at"])
        return locked

    @staticmethod
    @transaction.atomic
    def decrease_quantity(*, product, amount):
        if amount <= 0:
            raise ApplicationError("Amount must be a positive integer.")
        locked = Product.objects.select_for_update().get(pk=product.pk)
        if locked.quantity - amount < 0:
            raise ConflictError("Insufficient quantity available.")
        locked.quantity -= amount
        locked.save(update_fields=["quantity", "updated_at"])
        return locked
