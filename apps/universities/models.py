from django.db import models

from apps.common.fields import CloudinaryImageField
from apps.common.mixins import AutoSlugMixin
from apps.common.models import BaseModel

from .managers import UniversityManager


class University(AutoSlugMixin, BaseModel):
    """
    Represents a supported university/campus. Anchors user scoping, vendor
    eligibility, and product visibility boundaries per the "strict
    university scoping" product decision.
    """

    slug_source_field = "name"
    slug_field_name = "slug"
    slug_max_length = 160

    name = models.CharField(max_length=150, unique=True)
    short_name = models.CharField(max_length=20, unique=True)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    logo = CloudinaryImageField(folder="universities/logos", blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    objects = UniversityManager()

    class Meta:
        verbose_name = "University"
        verbose_name_plural = "Universities"
        ordering = ["name"]

    def __str__(self):
        return self.short_name
