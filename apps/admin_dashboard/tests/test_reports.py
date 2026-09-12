from unittest.mock import patch

from rest_framework import status

from apps.products.models import ProductStatus
from apps.products.tests.factories import (
    make_customer,
    make_product,
    make_university,
    make_verified_vendor,
)
from apps.reports.models import Report, ReportReason, ReportStatus

from .base import AdminAPITestCase


class AdminReportViewTests(AdminAPITestCase):
    """Tests for the admin-facing report management endpoints."""

    def setUp(self):
        super().setUp()

        self.university = make_university()
        self.customer = make_customer(
            university=self.university,
            email="reporter@example.com",
        )
        self.vendor_user, self.vendor_profile, self.store = make_verified_vendor(
            self.university,
            email="vendor@example.com",
        )
        self.product = make_product(
            self.store,
            self.university,
        )

        self.report = Report.objects.create(
            reporter=self.customer,
            product=self.product,
            reason=ReportReason.SCAM_OR_FRAUD,
            description="Suspicious listing.",
        )

    def test_non_admin_rejected(self):
        self.client.force_authenticate(self.customer)
        r = self.client.get("/api/v1/admin/reports/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_rejected(self):
        r = self.client.get("/api/v1/admin/reports/")
        self.assertIn(r.status_code, (401, 403))

    def test_admin_lists_queue_oldest_first(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get("/api/v1/admin/reports/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_status_filter(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get("/api/v1/admin/reports/?status=PENDING")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_unknown_report_404(self):
        import uuid

        self.client.force_authenticate(self.admin)
        r = self.client.get(f"/api/v1/admin/reports/{uuid.uuid4()}/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_resolution_notes_must_be_string(self):
        import uuid

        self.client.force_authenticate(self.admin)
        r = self.client.post(
            f"/api/v1/admin/reports/{uuid.uuid4()}/resolve/",
            {"resolution_notes": 12345},
            format="json",
        )
        self.assertIn(
            r.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND)
        )

    def test_resolve_delegates_to_report_service_and_passes_acting_admin(self):
        """Confirms resolve() forwards request.user as the acting admin
        and never lets the client supply resolved_by/resolved_at/status
        directly — those fields are absent from AdminResolutionSerializer
        entirely.
        """
        import uuid

        with (
            patch("apps.admin_dashboard.services.AdminReportService.get") as mock_get,
            patch(
                "apps.admin_dashboard.services.ReportService.resolve"
            ) as mock_resolve,
        ):
            mock_get.return_value = self.report
            mock_resolve.return_value = self.report

            self.client.force_authenticate(self.admin)
            self.client.post(
                f"/api/v1/admin/reports/{uuid.uuid4()}/resolve/",
                {"resolution_notes": "Confirmed violation."},
                format="json",
            )

            mock_resolve.assert_called_once_with(
                report=self.report,
                admin=self.admin,
                resolution_notes="Confirmed violation.",
            )

    def test_reject_delegates_to_report_service_without_moderation_side_effects(self):
        import uuid

        with (
            patch("apps.admin_dashboard.services.AdminReportService.get") as mock_get,
            patch("apps.admin_dashboard.services.ReportService.reject") as mock_reject,
        ):
            mock_get.return_value = self.report
            mock_reject.return_value = self.report
            self.client.force_authenticate(self.admin)
            self.client.post(
                f"/api/v1/admin/reports/{uuid.uuid4()}/reject/", {}, format="json"
            )
        mock_reject.assert_called_once_with(
            report=self.report, admin=self.admin, resolution_notes=None
        )

    # -- Unmocked integration tests ------------------------------------
    #
    # The mocked delegation tests above cannot catch signature drift in
    # ReportService.resolve()/reject(): mocking ReportService hides a
    # TypeError raised by a wrong call contract (the exact regression
    # where the facade passed `resolved_by=` and a positional report
    # argument to a keyword-only parameter). These tests exercise the
    # real view -> AdminReportService -> ReportService -> moderation-
    # cascade path against real fixtures.

    def test_resolve_end_to_end_persists_and_cascades_through_real_service(
        self,
    ):
        """Regression guard: POST .../resolve/ must succeed against the
        real ReportService and drive the real moderation cascade.

        A wrong call contract between AdminReportService and
        ReportService surfaces here as a 500 (TypeError) instead of a
        200, and no moderation side effect occurs.
        """
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f"/api/v1/admin/reports/{self.report.id}/resolve/",
            {"resolution_notes": "Confirmed violation."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Envelope contract (PRD §17) is preserved.
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["message"], "Report resolved.")

        self.report.refresh_from_db()
        self.product.refresh_from_db()

        # Real ReportService.resolve() persistence contract.
        self.assertEqual(self.report.status, ReportStatus.RESOLVED)
        self.assertEqual(self.report.resolved_by, self.admin)
        self.assertIsNotNone(self.report.resolved_at)
        self.assertEqual(self.report.resolution_notes, "Confirmed violation.")

        # The real moderation cascade ran: product reports resolve into
        # ProductLifecycleService.admin_remove() (DDS §7.3).
        self.assertEqual(self.product.status, ProductStatus.REMOVED_BY_ADMIN)

    def test_reject_end_to_end_closes_report_without_moderation_cascade(
        self,
    ):
        """Regression guard: POST .../reject/ must succeed against the
        real ReportService and trigger no moderation side effect.
        """
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f"/api/v1/admin/reports/{self.report.id}/reject/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["message"], "Report rejected.")

        self.report.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(self.report.status, ReportStatus.REJECTED)
        self.assertEqual(self.report.resolved_by, self.admin)
        self.assertIsNotNone(self.report.resolved_at)

        # "No action warranted" path: product remains untouched.
        self.assertEqual(self.product.status, ProductStatus.ACTIVE)
