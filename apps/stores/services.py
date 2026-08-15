from django.db import transaction

from apps.common.exceptions import ConflictError

from .models import Store

_UNSET = object()


class StoreService:
    @staticmethod
    @transaction.atomic
    def create(
        *, vendor_profile, display_name=None, description=None, contact_phone=None
    ):
        """
        Creates the single `Store` owned by `vendor_profile`.

        - `display_name` defaults to `vendor_profile.store_name` when omitted.
        - `contact_phone` defaults to `vendor_profile.phone_number` when omitted.
        - `is_active` is never accepted here; always the model default (`True`).
        - `slug` is never accepted here; derived by `AutoSlugMixin` from
          `display_name` on first save.
        """
        if hasattr(vendor_profile, "store"):
            raise ConflictError("This vendor already has a store.")

        store = Store.objects.create(
            vendor_profile=vendor_profile,
            display_name=display_name
            if display_name is not None
            else vendor_profile.store_name,
            description=description,
            contact_phone=(
                contact_phone
                if contact_phone is not None
                else vendor_profile.phone_number
            ),
        )
        return store

    @staticmethod
    @transaction.atomic
    def update(*, store, display_name=_UNSET, description=_UNSET, contact_phone=_UNSET):
        """
        Updates only explicitly-provided storefront fields (`display_name`,
        `description`, `contact_phone`).
        """
        update_fields = []

        if display_name is not _UNSET:
            store.display_name = display_name
            update_fields.append("display_name")
        if description is not _UNSET:
            store.description = description
            update_fields.append("description")
        if contact_phone is not _UNSET:
            store.contact_phone = contact_phone
            update_fields.append("contact_phone")

        if update_fields:
            update_fields.append("updated_at")
            store.save(update_fields=update_fields)
        return store

    @staticmethod
    @transaction.atomic
    def delete(*, store):
        """
        Soft-deletes the store via `BaseModel`'s default `.delete()` behavior (common app) — no `hard=True`, consistent with the
        project's soft-delete-by-default convention
        """
        store.delete()
        return store

    @staticmethod
    @transaction.atomic
    def set_active_state(*, store, is_active):
        """
        Toggles `Store.is_active`.
        """
        if store.is_active != is_active:
            store.is_active = is_active
            store.save(update_fields=["is_active", "updated_at"])
        return store
