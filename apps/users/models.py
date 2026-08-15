"""User model — apps.users."""

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel
from apps.common.validators import validate_phone_number
from apps.universities.models import University

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """The single identity record for every account

    Customer is the default, implicit role for every row in this table
    """

    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(
        max_length=20, blank=True, validators=[validate_phone_number]
    )
    active_university = models.ForeignKey(
        University,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
        help_text="Nullable until onboarding completes; changeable anytime (PRD §3).",
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        super().save(*args, **kwargs)

    @property
    def is_vendor(self):
        return hasattr(self, "vendor_profile")

    @property
    def is_admin(self):
        """Computed from `is_staff` / `is_superuser`"""
        return self.is_staff or self.is_superuser
