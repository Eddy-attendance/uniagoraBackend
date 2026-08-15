from datetime import timedelta

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.utils import timezone

from apps.categories.models import Category
from apps.common.fields import CloudinaryImageField
from apps.common.mixins import AutoSlugMixin
from apps.common.models import BaseModel
from apps.stores.models import Store
from apps.universities.models import University

from .managers import ProductManager


class ProductCondition(models.TextChoices):
    """Product.condition"""

    NEW = "NEW", "New"
    USED = "USED", "Used"


class ProductStatus(models.TextChoices):
    """Product.status.

    Deliberately has NO `OUT_OF_STOCK` value. "Out of Stock" is a derived
    condition (`quantity == 0`)
    """

    ACTIVE = "ACTIVE", "Active"
    EXPIRED = "EXPIRED", "Expired"
    HIDDEN_BY_SUSPENSION = "HIDDEN_BY_SUSPENSION", "Hidden by suspension"
    REMOVED_BY_ADMIN = "REMOVED_BY_ADMIN", "Removed by admin"


class Product(AutoSlugMixin, BaseModel):
    EXPIRY_DAYS = 30

    slug_source_field = "name"
    slug_field_name = "slug"
    slug_max_length = 220

    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name="products",
    )
    university = models.ForeignKey(
        University,
        on_delete=models.PROTECT,
        related_name="products",
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    condition = models.CharField(max_length=10, choices=ProductCondition.choices)
    quantity = models.PositiveIntegerField(default=1)
    campus_location = models.CharField(  # noqa: DJ001
        max_length=150,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=25,
        choices=ProductStatus.choices,
        default=ProductStatus.ACTIVE,
        db_index=True,
    )
    views_count = models.PositiveIntegerField(default=0)
    listed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    search_vector = SearchVectorField(null=True, blank=True)

    objects = ProductManager()

    class Meta:
        indexes = [
            models.Index(
                fields=["university", "status"], name="product_univ_status_idx"
            ),
            GinIndex(fields=["search_vector"], name="product_search_vector_gin"),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(price__gte=0), name="product_price_gte_0"
            ),
            models.CheckConstraint(
                check=models.Q(quantity__gte=0), name="product_quantity_gte_0"
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self._state.adding and self.expires_at is None:
            self.expires_at = timezone.now() + timedelta(days=self.EXPIRY_DAYS)
        super().save(*args, **kwargs)

    @property
    def is_out_of_stock(self):
        """Derived from quantity — never a stored status value"""
        return self.quantity == 0

    @property
    def primary_image(self):
        return self.images.alive().filter(is_primary=True).first()


class ProductImage(BaseModel):
    """Up to eight images per product; exactly one marked primary."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = CloudinaryImageField(folder="products")
    is_primary = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_primary=True),
                name="unique_primary_image_per_product",
            ),
        ]

    def __str__(self):
        return f"{self.product.name} image #{self.display_order}"


class ProductCategory(BaseModel):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="category_links"
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="product_links"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "category"], name="unique_product_category"
            ),
        ]
        indexes = [
            models.Index(
                fields=["category", "product"], name="productcategory_cat_prod_idx"
            ),
        ]
