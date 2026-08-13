from django.test import TestCase

from apps.products.tests.factories import (
    make_customer,
    make_product,
    make_university,
    make_verified_vendor,
)
from apps.reports.models import Report, ReportReason
from apps.reports.serializers import (
    ReportAdminSerializer,
    ReportCreateSerializer,
    ReportResolutionSerializer,
    ReportSerializer,
)


class ReportSerializerTests(TestCase):
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

        self.report = Report.objects.create(
            reporter=self.customer,
            product=self.product,
            reason=ReportReason.SCAM_OR_FRAUD,
            description="Suspicious listing.",
        )

    def test_customer_serializer_excludes_internal_fields(self):
        data = ReportSerializer(self.report).data

        self.assertEqual(data["target_type"], "PRODUCT")
        self.assertEqual(str(data["target_id"]), str(self.product.id))
        self.assertEqual(data["reason"], ReportReason.SCAM_OR_FRAUD)

        self.assertNotIn("reporter", data)
        self.assertNotIn("resolved_by", data)
        self.assertNotIn("resolved_at", data)
        self.assertNotIn("resolution_notes", data)

    def test_admin_serializer_includes_internal_fields(self):
        data = ReportAdminSerializer(self.report).data

        self.assertIn("reporter", data)
        self.assertIn("reporter_name", data)
        self.assertIn("resolved_by", data)
        self.assertIn("resolved_by_name", data)
        self.assertIn("resolved_at", data)
        self.assertIn("resolution_notes", data)

    def test_create_serializer_accepts_normal_reason_without_description(self):
        serializer = ReportCreateSerializer(data={"reason": ReportReason.SCAM_OR_FRAUD})

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_create_serializer_requires_description_for_other(self):
        serializer = ReportCreateSerializer(data={"reason": ReportReason.OTHER})

        self.assertFalse(serializer.is_valid())
        self.assertIn("description", serializer.errors)

    def test_create_serializer_rejects_blank_other_description(self):
        serializer = ReportCreateSerializer(
            data={
                "reason": ReportReason.OTHER,
                "description": "   ",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("description", serializer.errors)

    def test_create_serializer_accepts_other_with_description(self):
        serializer = ReportCreateSerializer(
            data={
                "reason": ReportReason.OTHER,
                "description": "Detailed explanation.",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_create_serializer_does_not_accept_target_fields(self):
        serializer = ReportCreateSerializer(
            data={
                "reason": ReportReason.SCAM_OR_FRAUD,
                "product": str(self.product.id),
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("product", serializer.validated_data)

    def test_resolution_serializer_allows_missing_notes(self):
        serializer = ReportResolutionSerializer(data={})

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_resolution_serializer_allows_blank_notes(self):
        serializer = ReportResolutionSerializer(data={"resolution_notes": ""})

        self.assertTrue(serializer.is_valid(), serializer.errors)
