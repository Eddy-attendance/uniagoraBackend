from django.db import transaction

from apps.common.exceptions import ApplicationError, ConflictError

from ..models import Product


class InventoryService:
    @staticmethod
    @transaction.atomic
    def set_quantity(*, product, quantity):
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
