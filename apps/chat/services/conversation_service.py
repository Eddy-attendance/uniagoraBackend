from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.chat.models import Conversation, TransactionStatus
from apps.common.exceptions import (
    ApplicationError,
    ConflictError,
    PermissionDeniedError,
)
from apps.vendors.models import VendorProfile


class ConversationService:
    @staticmethod
    @transaction.atomic
    def initiate(*, customer, vendor, product=None):
        # Row lock acquired first so every check (including
        # `is_verified`) reads a value that cannot change out from under
        # this request for the rest of the transaction.
        locked_vendor = VendorProfile.objects.select_for_update().get(pk=vendor.pk)

        if not locked_vendor.is_verified:
            raise ConflictError("This vendor is not currently accepting messages.")

        if getattr(locked_vendor, "user_id", None) == getattr(customer, "id", None):
            raise ConflictError("You cannot start a conversation with your own store.")

        if product is not None and product.store.vendor_profile_id != locked_vendor.id:
            raise ApplicationError(
                "The selected product does not belong to this vendor.",
                errors={
                    "product": ["Product does not belong to the specified vendor."]
                },
            )

        existing = (
            Conversation.objects.alive()
            .filter(customer=customer, vendor=locked_vendor, product=product)
            .first()
        )
        if existing is not None:
            return existing, False

        try:
            with transaction.atomic():
                conversation = Conversation.objects.create(
                    customer=customer, vendor=locked_vendor, product=product
                )
            return conversation, True
        except IntegrityError:
            existing = (
                Conversation.objects.alive()
                .filter(customer=customer, vendor=locked_vendor, product=product)
                .first()
            )
            if existing is not None:
                return existing, False
            raise

    @staticmethod
    @transaction.atomic
    def mark_completed(*, conversation, actor):
        locked_conversation = (
            Conversation.objects.select_for_update()
            .select_related("vendor")
            .get(pk=conversation.pk)
        )

        if getattr(locked_conversation.vendor, "user_id", None) != getattr(
            actor, "id", None
        ):
            raise PermissionDeniedError(
                "Only the vendor of this conversation may mark the transaction as completed."
            )

        if locked_conversation.transaction_status == TransactionStatus.COMPLETED:
            raise ConflictError("This transaction has already been marked completed.")

        locked_conversation.transaction_status = TransactionStatus.COMPLETED
        locked_conversation.completed_at = timezone.now()
        locked_conversation.save(
            update_fields=["transaction_status", "completed_at", "updated_at"]
        )
        return locked_conversation
