from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import BaseModel


class Review(BaseModel):
    """A Customer's rating/comment on a completed transaction"""

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

    def __str__(self):
        return f"{self.rating}★ for {self.store.display_name}"

    @property
    def is_edited(self):
        return self.edited_at is not None
