from django.db import IntegrityError, transaction

from apps.common.exceptions import ConflictError

from .models import Category

_UNSET = object()


class CategoryService:
    """Static-method service layer for `Category`. No instance state."""

    @staticmethod
    @transaction.atomic
    def create(*, name, parent=None, display_order=0):
        try:
            with transaction.atomic():
                return Category.objects.create(
                    name=name,
                    parent=parent,
                    display_order=display_order,
                )
        except IntegrityError as exc:
            raise ConflictError(
                "A category with this name already exists at this level."
            ) from exc

    @staticmethod
    @transaction.atomic
    def update(*, category, name=_UNSET):
        if name is not _UNSET:
            category.name = name
            category.save(update_fields=["name", "updated_at"])
        return category

    @staticmethod
    @transaction.atomic
    def activate(*, category):
        if category.is_active:
            raise ConflictError("Category is already active.")
        category.is_active = True
        category.save(update_fields=["is_active", "updated_at"])
        return category

    @staticmethod
    @transaction.atomic
    def deactivate(*, category):
        if not category.is_active:
            raise ConflictError("Category is already inactive.")
        category.is_active = False
        category.save(update_fields=["is_active", "updated_at"])
        return category

    @staticmethod
    @transaction.atomic
    def delete(*, category):
        """Soft-delete a category."""
        blocking_children = category.children.alive()
        if blocking_children.exists():
            raise ConflictError(
                "Category has subcategories that must be deleted first."
            )
        category.delete()
        return category
