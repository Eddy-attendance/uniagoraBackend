"""
Service layer for Reviews.

Owns the review business rules defined by DDS §7.3:
- creation eligibility
- one-review-per-conversation
- ownership on create/edit
- rating validation
- server-derived, immutable store denormalization

Views and serializers do not implement these domain rules directly.
"""

from django.db import transaction
from django.utils import timezone

from apps.chat.models import Conversation, TransactionStatus
from apps.common.exceptions import (
    ApplicationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from apps.stores.models import Store

from .models import Review

# Local sentinel. This is intentionally not promoted to common because
# it has only one consumer.
_UNSET = object()

_MIN_RATING = 1
_MAX_RATING = 5


def _validate_rating(rating):
    """Validate the Review domain's rating invariant."""
    if isinstance(rating, bool) or not isinstance(rating, int):
        raise ApplicationError("Rating must be an integer between 1 and 5.")

    if not _MIN_RATING <= rating <= _MAX_RATING:
        raise ApplicationError("Rating must be between 1 and 5.")


class ReviewService:
    @staticmethod
    def get_for_conversation(*, conversation):
        """Return the active review associated with a conversation."""
        review = Review.objects.alive().filter(conversation=conversation).first()

        if review is None:
            raise NotFoundError("No review exists for this conversation yet.")

        return review

    @staticmethod
    def create(*, conversation, customer, rating, comment=None):
        """
        Create a review for a completed conversation.

        Rules enforced:
        1. Only the conversation's customer may create the review.
        2. Rating must be between 1 and 5.
        3. The conversation must be COMPLETED.
        4. Only one review may exist for a conversation.
        5. Store is derived server-side from the conversation's vendor.
        6. Conversation.transaction_status is never mutated.
        """
        if conversation.customer_id != customer.id:
            raise PermissionDeniedError(
                "Only the customer in this conversation may leave a review."
            )

        _validate_rating(rating)

        with transaction.atomic():
            locked_conversation = (
                Conversation.objects.select_for_update()
                .select_related("vendor")
                .get(pk=conversation.pk)
            )

            if locked_conversation.transaction_status != TransactionStatus.COMPLETED:
                raise ConflictError(
                    "Reviews can only be created after the vendor marks "
                    "the transaction as completed."
                )

            if hasattr(locked_conversation, "review"):
                raise ConflictError("This conversation already has a review.")

            try:
                store = locked_conversation.vendor.store
            except Store.DoesNotExist:
                raise NotFoundError(
                    "The vendor for this conversation does not have a store yet."
                ) from None

            return Review.objects.create(
                conversation=locked_conversation,
                store=store,
                rating=rating,
                comment=comment,
            )

    @staticmethod
    def update(*, review, actor, rating=_UNSET, comment=_UNSET):
        """
        Update a review owned by the requesting customer.

        `store` and `conversation` are deliberately absent from the
        signature, making them structurally immutable through this service.
        """
        if review.conversation.customer_id != actor.id:
            raise PermissionDeniedError("Only the review's author may edit it.")

        update_fields = []

        if rating is not _UNSET:
            _validate_rating(rating)
            review.rating = rating
            update_fields.append("rating")

        if comment is not _UNSET:
            review.comment = comment
            update_fields.append("comment")

        if update_fields:
            review.edited_at = timezone.now()
            update_fields.extend(["edited_at", "updated_at"])
            review.save(update_fields=update_fields)

        return review
