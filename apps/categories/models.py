from django.db import models

from apps.common.mixins import AutoSlugMixin
from apps.common.models import BaseModel

from .managers import CategoryManager


class Category(AutoSlugMixin, BaseModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        null=True,
        blank=True,
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    slug_source_field = "name"
    slug_field_name = "slug"
    slug_max_length = 120

    objects = CategoryManager()

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=models.Q(parent__isnull=True, is_deleted=False),
                name="unique_alive_root_category_name",
            ),
            models.UniqueConstraint(
                fields=["parent", "name"],
                condition=models.Q(parent__isnull=False, is_deleted=False),
                name="unique_alive_child_category_name_per_parent",
            ),
        ]
        indexes = [
            models.Index(
                fields=["parent", "display_order"],
                name="category_parent_order_idx",
            ),
        ]

    def __str__(self):
        if self.parent_id and self.parent:
            return f"{self.parent} > {self.name}"
        return self.name

    @property
    def is_root(self):
        return self.parent_id is None
