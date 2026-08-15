from django.db import models

from apps.common.mixins import AutoSlugMixin
from apps.common.models import BaseModel
from apps.common.validators import validate_phone_number


class Store(AutoSlugMixin, BaseModel):
    """
    The public-facing storefront a Customer sees
    """

    vendor_profile = models.OneToOneField(
        "vendors.VendorProfile",
        on_delete=models.CASCADE,
        related_name="store",
    )
    display_name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True)
    description = models.TextField(  # noqa: DJ001
        null=True, blank=True
    )
    contact_phone = models.CharField(  # noqa: DJ001
        max_length=20,
        null=True,
        blank=True,
        validators=[validate_phone_number],
    )
    is_active = models.BooleanField(default=True, db_index=True)

    slug_source_field = "display_name"
    slug_field_name = "slug"
    slug_max_length = 170

    def __str__(self):
        return self.display_name
