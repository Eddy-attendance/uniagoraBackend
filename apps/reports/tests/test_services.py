from django.test import TestCase

from apps.common.exceptions import ApplicationError, ConflictError
from apps.products.models import ProductStatus
from apps.products.tests.factories import (
    make_customer,
    make_product,
    make_university,
    make_verified_vendor,
)
from apps.reports.models import Report, ReportReason, ReportStatus
from apps.reports.services import ReportService
from apps.vendors.models import VendorStatus


class ReportServiceTestsBase(TestCase):
    def setUp(self):
        self.university = make_university()

        self.customer = make_customer(
            university=self.university,
            email="customer@example.com",
        )

        self.admin = make_customer(
            university=self.university,
            email="admin@example.com",
            is_staff=True,
        )

        (
            self.vendor_user,
            self.vendor_profile,
            self.store,
        ) = make_verified_vendor(
            self.university,
            email="vendor@example.com",
        )

        self.product = make_product(
            self.store,
            self.university,
        )


class ReportServiceCreateTests(ReportServiceTestsBase):
    def test_create_product_report(self):
        report = ReportService.create_for_product(
            reporter=self.customer,
            product=self.product,
            reason=ReportReason.SCAM_OR_FRAUD,
            description="Suspicious listing.",
        )

        self.assertEqual(report.reporter, self.customer)
        self.assertEqual(report.product, self.product)
        self.assertIsNone(report.vendor_profile)
        self.assertEqual(report.status, ReportStatus.PENDING)

    def test_create_vendor_report(self):
        report = ReportService.create_for_vendor(
            reporter=self.customer,
            vendor_profile=self.vendor_profile,
            reason=ReportReason.FAKE_VENDOR,
        )

        self.assertEqual(report.vendor_profile, self.vendor_profile)
        self.assertEqual(report.status, ReportStatus.PENDING)

    def test_other_requires_description(self):
        with self.assertRaises(ApplicationError):
            ReportService.create_for_product(
                reporter=self.customer,
                product=self.product,
                reason=ReportReason.OTHER,
            )

    def test_other_rejects_blank_description(self):
        with self.assertRaises(ApplicationError):
            ReportService.create_for_product(
                reporter=self.customer,
                product=self.product,
                reason=ReportReason.OTHER,
                description="   ",
            )


class ReportServiceLifecycleTests(ReportServiceTestsBase):
    def make_product_report(self):
        return Report.objects.create(
            reporter=self.customer,
            product=self.product,
            reason=ReportReason.SCAM_OR_FRAUD,
        )

    def make_vendor_report(self):
        return Report.objects.create(
            reporter=self.customer,
            vendor_profile=self.vendor_profile,
            reason=ReportReason.FAKE_VENDOR,
        )

    def test_mark_under_review(self):
        report = self.make_product_report()

        updated = ReportService.mark_under_review(report=report)

        self.assertEqual(updated.status, ReportStatus.UNDER_REVIEW)

    def test_mark_under_review_rejects_non_pending_report(self):
        report = self.make_product_report()
        report.status = ReportStatus.UNDER_REVIEW
        report.save(update_fields=["status"])

        with self.assertRaises(ConflictError):
            ReportService.mark_under_review(report=report)

    def test_resolve_product_report_removes_product(self):
        report = self.make_product_report()

        ReportService.resolve(
            report=report,
            admin=self.admin,
            resolution_notes="Confirmed prohibited listing.",
        )

        report.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(report.status, ReportStatus.RESOLVED)
        self.assertEqual(report.resolved_by, self.admin)
        self.assertIsNotNone(report.resolved_at)
        self.assertEqual(
            report.resolution_notes,
            "Confirmed prohibited listing.",
        )
        self.assertEqual(
            self.product.status,
            ProductStatus.REMOVED_BY_ADMIN,
        )

    def test_resolve_vendor_report_suspends_vendor(self):
        report = self.make_vendor_report()

        ReportService.resolve(
            report=report,
            admin=self.admin,
            resolution_notes="Confirmed fraudulent vendor.",
        )

        report.refresh_from_db()
        self.vendor_profile.refresh_from_db()

        self.assertEqual(report.status, ReportStatus.RESOLVED)
        self.assertEqual(
            self.vendor_profile.status,
            VendorStatus.SUSPENDED,
        )

    def test_vendor_resolution_cascades_to_store_and_products(self):
        report = self.make_vendor_report()

        ReportService.resolve(
            report=report,
            admin=self.admin,
        )

        self.store.refresh_from_db()
        self.product.refresh_from_db()

        self.assertFalse(self.store.is_active)
        self.assertEqual(
            self.product.status,
            ProductStatus.HIDDEN_BY_SUSPENSION,
        )

    def test_reject_does_not_moderate_product(self):
        report = self.make_product_report()

        ReportService.reject(
            report=report,
            admin=self.admin,
            resolution_notes="Evidence insufficient.",
        )

        report.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(report.status, ReportStatus.REJECTED)
        self.assertEqual(
            self.product.status,
            ProductStatus.ACTIVE,
        )

    def test_reject_does_not_suspend_vendor(self):
        report = self.make_vendor_report()

        ReportService.reject(
            report=report,
            admin=self.admin,
        )

        report.refresh_from_db()
        self.vendor_profile.refresh_from_db()

        self.assertEqual(report.status, ReportStatus.REJECTED)

    def test_pending_can_be_resolved_directly(self):
        report = self.make_product_report()

        ReportService.resolve(
            report=report,
            admin=self.admin,
        )

        report.refresh_from_db()

        self.assertEqual(report.status, ReportStatus.RESOLVED)

    def test_pending_can_be_rejected_directly(self):
        report = self.make_product_report()

        ReportService.reject(
            report=report,
            admin=self.admin,
        )

        report.refresh_from_db()

        self.assertEqual(report.status, ReportStatus.REJECTED)

    def test_resolved_report_cannot_be_resolved_again(self):
        report = self.make_product_report()

        ReportService.resolve(
            report=report,
            admin=self.admin,
        )

        with self.assertRaises(ConflictError):
            ReportService.resolve(
                report=report,
                admin=self.admin,
            )

    def test_rejected_report_cannot_be_rejected_again(self):
        report = self.make_product_report()

        ReportService.reject(
            report=report,
            admin=self.admin,
        )

        with self.assertRaises(ConflictError):
            ReportService.reject(
                report=report,
                admin=self.admin,
            )

    def test_rejected_report_cannot_be_resolved(self):
        report = self.make_product_report()

        ReportService.reject(
            report=report,
            admin=self.admin,
        )

        with self.assertRaises(ConflictError):
            ReportService.resolve(
                report=report,
                admin=self.admin,
            )

    def test_resolved_report_cannot_be_rejected(self):
        report = self.make_product_report()

        ReportService.resolve(
            report=report,
            admin=self.admin,
        )

        with self.assertRaises(ConflictError):
            ReportService.reject(
                report=report,
                admin=self.admin,
            )

    def test_failed_product_moderation_rolls_back_report_resolution(self):
        report = self.make_product_report()

        self.product.status = ProductStatus.REMOVED_BY_ADMIN
        self.product.save(update_fields=["status"])

        with self.assertRaises(ConflictError):
            ReportService.resolve(
                report=report,
                admin=self.admin,
            )

        report.refresh_from_db()

        self.assertEqual(
            report.status,
            ReportStatus.PENDING,
        )
        self.assertIsNone(report.resolved_by)
        self.assertIsNone(report.resolved_at)

    def test_failed_vendor_moderation_rolls_back_report_resolution(self):
        report = self.make_vendor_report()

        self.vendor_profile.status = VendorStatus.SUSPENDED
        self.vendor_profile.save(update_fields=["status"])

        with self.assertRaises(ConflictError):
            ReportService.resolve(
                report=report,
                admin=self.admin,
            )

        report.refresh_from_db()

        self.assertEqual(
            report.status,
            ReportStatus.PENDING,
        )
        self.assertIsNone(report.resolved_by)
        self.assertIsNone(report.resolved_at)
