"""
Review — DDS §4.13. Owned exclusively by `reviews`. Eligibility
(`Conversation.transaction_status == COMPLETED`) is enforced entirely in
`services.py`; this module contains persistence logic only, per
Architecture §7 ("business logic belongs in services, never models").

No managers.py: DDS names no Review-specific query shape beyond what
BaseModel's inherited SoftDeleteManager (`.alive()`/`.dead()`) already
gives — mirrors the precedent set by `vendors`, `stores`, and `categories`
(no manager file without a DDS-named method).
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import BaseModel


class Review(BaseModel):
    """A Customer's rating/comment on a completed transaction (DDS §4.13).

    `conversation` is the eligibility anchor (OneToOne — one review per
    completed thread). `store` is an intentional, documented
    denormalization (DDS §4.13 / Architecture §4) copied once at creation
    from `conversation.vendor.store` — never a source of truth on its own,
    never client-writable, immutable after creation (enforced in
    `services.ReviewService`, which has no `store` parameter on `update`).
    """

    conversation = models.OneToOneField(
        "chat.Conversation",
        on_delete=models.PROTECT,
        related_name="review",
    )
    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.PROTECT,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(  # noqa: DJ001
        null=True, blank=True
    )
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="review_rating_between_1_and_5",
            ),
        ]
        # No Meta.ordering override: BaseModel's inherited "-created_at"
        # already matches DDS §11's named "Review listing (storefront)"
        # query pattern (`.filter(store=store).order_by('-created_at')`).
        # `store` and `conversation` each get their DB index for free —
        # `ForeignKey`/`OneToOneField` auto-index their column in Django;
        # no explicit Meta.indexes entry duplicates that.

    def __str__(self):
        return f"{self.rating}★ for {self.store.display_name}"

    @property
    def is_edited(self):
        return self.edited_at is not None
