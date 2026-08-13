from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, Q

from apps.common.models import BaseModel


class ReportReason(models.TextChoices):
    PROHIBITED_ITEM = "PROHIBITED_ITEM", "Prohibited Item"
    MISLEADING_LISTING = "MISLEADING_LISTING", "Misleading Listing"
    SCAM_OR_FRAUD = "SCAM_OR_FRAUD", "Scam or Fraud"
    INAPPROPRIATE_BEHAVIOR = "INAPPROPRIATE_BEHAVIOR", "Inappropriate Behavior"
    FAKE_VENDOR = "FAKE_VENDOR", "Fake Vendor"
    OTHER = "OTHER", "Other"


class ReportStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    RESOLVED = "RESOLVED", "Resolved"
    REJECTED = "REJECTED", "Rejected"


class Report(BaseModel):
    """
    A Customer's report of a Product or a Vendor, for Admin moderation
    (DDS §4.14).

    `reports` owns this model and its lifecycle only (PENDING ->
    UNDER_REVIEW -> RESOLVED/REJECTED, DDS §9.7). It does NOT own product
    removal or vendor suspension logic — those remain in
    `products.services.lifecycle_service.ProductLifecycleService` and
    `vendors.services.VendorSuspensionService` respectively. See
    `services.ReportService.resolve()`, which calls into those services
    rather than mutating `Product`/`VendorProfile` directly (Architecture
    §2: reports "Does NOT own: Product/vendor suspension actions
    themselves").
    """

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reports_filed",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="reports",
        null=True,
        blank=True,
    )
    vendor_profile = models.ForeignKey(
        "vendors.VendorProfile",
        on_delete=models.CASCADE,
        related_name="reports",
        null=True,
        blank=True,
    )
    reason = models.CharField(max_length=30, choices=ReportReason.choices)
    description = models.TextField(  # noqa: DJ001
        null=True, blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
        db_index=True,
    )
    resolved_by = models.ForeignKey(  # noqa: DJ001
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reports_resolved",
        null=True,
        blank=True,
    )
    resolved_at = models.DateTimeField(  # noqa: DJ001
        null=True, blank=True
    )
    resolution_notes = models.TextField(  # noqa: DJ001
        null=True, blank=True
    )

    class Meta:
        constraints = [
            # DDS §4.14 Constraints: exactly one of product/vendor_profile
            # non-null. Modeled as an explicit XOR of the two nullable FKs
            # rather than num_nonnulls(), since Django's ORM has no direct
            # equivalent — semantically identical.
            CheckConstraint(
                check=(
                    Q(product__isnull=False, vendor_profile__isnull=True)
                    | Q(product__isnull=True, vendor_profile__isnull=False)
                ),
                name="report_exactly_one_target",
            ),
            # DDS §5, ReportReason.OTHER note: "Free-text elaboration
            # required in description." Not listed in DDS §4.14's own
            # "Constraints" bullet list (which only names the target-XOR
            # check) — this DB-level backstop is an added Engineering
            # Decision, consistent with the project's "service-enforced +
            # DB backstop" philosophy. See ADR-REP1 in the README.
            CheckConstraint(
                check=(
                    ~Q(reason=ReportReason.OTHER)
                    | (Q(description__isnull=False) & ~Q(description=""))
                ),
                name="report_other_reason_requires_description",
            ),
        ]
        # No explicit db_index on product/vendor_profile beyond the
        # implicit FK index Django already creates for every ForeignKey —
        # this already satisfies DDS §6's "product_id, vendor_profile_id
        # (each, nullable) — B-tree" requirement without a duplicate index.

    def __str__(self):
        return f"{self.target_label} report — {self.get_status_display()}"

    @property
    def target(self):
        """Returns whichever of product/vendor_profile is set (DDS §4.14)."""
        return self.product or self.vendor_profile

    @property
    def target_label(self):
        if self.product_id:
            return f"Product({self.product_id})"
        return f"Vendor({self.vendor_profile_id})"
