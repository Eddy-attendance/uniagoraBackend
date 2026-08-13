from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import ApplicationError, ConflictError
from apps.products.services.lifecycle_service import ProductLifecycleService
from apps.vendors.services import VendorSuspensionService

from .models import Report, ReportReason, ReportStatus


class ReportService:
    """
    Owns Report lifecycle transitions only.

    resolve() and reject() both close a report, but per DDS §5's status
    definitions ("RESOLVED = Action taken", "REJECTED = No action
    warranted"), only resolve() triggers the corresponding moderation
    action against the report's target. This is an Engineering Decision
    — no frozen document spells out the exact call sequence — see the
    README's Assumption 2.
    """

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_reason_description(reason, description):
        """Backstops the OTHER-requires-description rule at the service
        layer, ahead of the DB CheckConstraint (DDS §5 note on
        ReportReason.OTHER)."""
        if reason == ReportReason.OTHER and not (description and description.strip()):
            raise ApplicationError(
                message="Description is required when reason is 'OTHER'.",
                errors={
                    "description": ["This field is required when reason is OTHER."]
                },
            )

    @staticmethod
    @transaction.atomic
    def create_for_product(*, reporter, product, reason, description=None):
        ReportService._validate_reason_description(reason, description)
        return Report.objects.create(
            reporter=reporter,
            product=product,
            reason=reason,
            description=description,
        )

    @staticmethod
    @transaction.atomic
    def create_for_vendor(*, reporter, vendor_profile, reason, description=None):
        ReportService._validate_reason_description(reason, description)
        return Report.objects.create(
            reporter=reporter,
            vendor_profile=vendor_profile,
            reason=reason,
            description=description,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def mark_under_review(*, report):
        """PENDING -> UNDER_REVIEW. ConflictError (409) otherwise."""
        report = Report.objects.select_for_update().get(pk=report.pk)
        if report.status != ReportStatus.PENDING:
            raise ConflictError("Only a pending report can be moved to under review.")
        report.status = ReportStatus.UNDER_REVIEW
        report.save(update_fields=["status", "updated_at"])
        return report

    @staticmethod
    @transaction.atomic
    def resolve(*, report, admin, resolution_notes=None):
        """
        PENDING/UNDER_REVIEW -> RESOLVED, and triggers the moderation
        action matching the report's target:
          - product-targeted report -> ProductLifecycleService.admin_remove()
          - vendor-targeted report  -> VendorSuspensionService.suspend()

        Wrapped in transaction.atomic(): if the downstream service call
        fails (e.g. the target is already in a conflicting state), the
        whole resolution rolls back and the report remains open —
        `reports` never silently marks something resolved without the
        action it claims to represent actually having happened.
        """
        report = Report.objects.select_for_update().get(pk=report.pk)
        if report.status in (ReportStatus.RESOLVED, ReportStatus.REJECTED):
            raise ConflictError("Report has already been closed.")

        if report.product_id:
            ProductLifecycleService.admin_remove(product=report.product)
        else:
            VendorSuspensionService.suspend(vendor_profile=report.vendor_profile)

        report.status = ReportStatus.RESOLVED
        report.resolved_by = admin
        report.resolved_at = timezone.now()
        report.resolution_notes = resolution_notes
        report.save(
            update_fields=[
                "status",
                "resolved_by",
                "resolved_at",
                "resolution_notes",
                "updated_at",
            ]
        )
        return report

    @staticmethod
    @transaction.atomic
    def reject(*, report, admin, resolution_notes=None):
        """PENDING/UNDER_REVIEW -> REJECTED. No moderation action is
        triggered — this is the "no action warranted" path (DDS §5)."""
        report = Report.objects.select_for_update().get(pk=report.pk)
        if report.status in (ReportStatus.RESOLVED, ReportStatus.REJECTED):
            raise ConflictError("Report has already been closed.")

        report.status = ReportStatus.REJECTED
        report.resolved_by = admin
        report.resolved_at = timezone.now()
        report.resolution_notes = resolution_notes
        report.save(
            update_fields=[
                "status",
                "resolved_by",
                "resolved_at",
                "resolution_notes",
                "updated_at",
            ]
        )
        return report
