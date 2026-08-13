from django.db import IntegrityError
from django.test import TestCase

from apps.products.tests.factories import (
    make_customer,
    make_product,
    make_university,
    make_verified_vendor,
)
from apps.reports.models import Report, ReportReason, ReportStatus


class ReportModelTests(TestCase):
    def setUp(self):
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

    def test_product_report_can_be_created(self):
        report = Report.objects.create(
            reporter=self.customer,
            product=self.product,
            reason=ReportReason.SCAM_OR_FRAUD,
        )

        self.assertEqual(report.status, ReportStatus.PENDING)
        self.assertEqual(report.product, self.product)
        self.assertIsNone(report.vendor_profile)

    def test_vendor_report_can_be_created(self):
        report = Report.objects.create(
            reporter=self.customer,
            vendor_profile=self.vendor_profile,
            reason=ReportReason.FAKE_VENDOR,
        )

        self.assertEqual(report.status, ReportStatus.PENDING)
        self.assertEqual(report.vendor_profile, self.vendor_profile)
        self.assertIsNone(report.product)

    def test_report_cannot_target_both_product_and_vendor(self):
        with self.assertRaises(IntegrityError):
            Report.objects.create(
                reporter=self.customer,
                product=self.product,
                vendor_profile=self.vendor_profile,
                reason=ReportReason.SCAM_OR_FRAUD,
            )

    def test_report_cannot_have_no_target(self):
        with self.assertRaises(IntegrityError):
            Report.objects.create(
                reporter=self.customer,
                reason=ReportReason.SCAM_OR_FRAUD,
            )

    def test_other_reason_requires_description_at_database_level(self):
        with self.assertRaises(IntegrityError):
            Report.objects.create(
                reporter=self.customer,
                product=self.product,
                reason=ReportReason.OTHER,
            )

    def test_other_reason_with_description_is_valid(self):
        report = Report.objects.create(
            reporter=self.customer,
            product=self.product,
            reason=ReportReason.OTHER,
            description="Something unusual happened.",
        )

        self.assertEqual(report.reason, ReportReason.OTHER)

    def test_normal_reason_does_not_require_description(self):
        report = Report.objects.create(
            reporter=self.customer,
            product=self.product,
            reason=ReportReason.PROHIBITED_ITEM,
        )

        self.assertIsNone(report.description)

    def test_target_property_returns_product(self):
        report = Report.objects.create(
            reporter=self.customer,
            product=self.product,
            reason=ReportReason.MISLEADING_LISTING,
        )

        self.assertEqual(report.target, self.product)

    def test_target_property_returns_vendor(self):
        report = Report.objects.create(
            reporter=self.customer,
            vendor_profile=self.vendor_profile,
            reason=ReportReason.FAKE_VENDOR,
        )

        self.assertEqual(report.target, self.vendor_profile)

    def test_target_label_for_product(self):
        report = Report.objects.create(
            reporter=self.customer,
            product=self.product,
            reason=ReportReason.PROHIBITED_ITEM,
        )

        self.assertEqual(
            report.target_label,
            f"Product({self.product.id})",
        )

    def test_target_label_for_vendor(self):
        report = Report.objects.create(
            reporter=self.customer,
            vendor_profile=self.vendor_profile,
            reason=ReportReason.FAKE_VENDOR,
        )

        self.assertEqual(
            report.target_label,
            f"Vendor({self.vendor_profile.id})",
        )
