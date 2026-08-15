from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import ApplicationError, ConflictError
from apps.products.services.lifecycle_service import ProductLifecycleService
from apps.vendors.services import VendorSuspensionService

from .models import Report, ReportReason, ReportStatus


class ReportService:
    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_reason_description(reason, description):
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
        triggered — this is the "no action warranted" path."""
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
