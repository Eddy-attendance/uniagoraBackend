from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.products.models import Product, ProductCondition, ProductStatus
from apps.reports.models import Report, ReportReason, ReportStatus
from apps.stores.models import Store
from apps.universities.models import University
from apps.users.models import User
from apps.vendors.models import VendorProfile, VendorStatus, VendorType


class ReportViewTestsBase(APITestCase):
    def setUp(self):
        self.university = University.objects.create(
            name="Test University",
            short_name="TU",
        )

        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="pass1234!",
            full_name="Test Customer",
        )

        self.other_customer = User.objects.create_user(
            email="other@example.com",
            password="pass1234!",
            full_name="Other Customer",
        )

        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="pass1234!",
            full_name="Test Admin",
            is_staff=True,
        )

        self.superuser = User.objects.create_superuser(
            email="superuser@example.com",
            password="pass1234!",
            full_name="Test Superuser",
        )

        self.vendor_user = User.objects.create_user(
            email="vendor@example.com",
            password="pass1234!",
            full_name="Test Vendor",
        )

        self.vendor_profile = VendorProfile.objects.create(
            user=self.vendor_user,
            university=self.university,
            vendor_type=VendorType.BUSINESS,
            store_name="Vendor Store",
            phone_number="+2348000000000",
            business_name="Vendor Business",
            business_address="1 Campus Road",
            status=VendorStatus.VERIFIED,
        )

        self.store = Store.objects.create(
            vendor_profile=self.vendor_profile,
            display_name="Vendor Store",
        )

        self.product = Product.objects.create(
            store=self.store,
            university=self.university,
            name="Test Product",
            description="A test product.",
            price=Decimal("100.00"),
            condition=ProductCondition.NEW,
            quantity=5,
        )

    def product_url(self):
        return f"/api/v1/reports/products/{self.product.id}/"

    def vendor_url(self):
        return f"/api/v1/reports/vendors/{self.vendor_profile.id}/"

    def report_url(self, report):
        return f"/api/v1/reports/{report.id}/"

    def under_review_url(self, report):
        return f"/api/v1/reports/{report.id}/under-review/"

    def resolve_url(self, report):
        return f"/api/v1/reports/{report.id}/resolve/"

    def reject_url(self, report):
        return f"/api/v1/reports/{report.id}/reject/"

    def create_product_report(self, **kwargs):
        defaults = {
            "reporter": self.customer,
            "product": self.product,
            "reason": ReportReason.SCAM_OR_FRAUD,
        }
        defaults.update(kwargs)
        return Report.objects.create(**defaults)

    def create_vendor_report(self, **kwargs):
        defaults = {
            "reporter": self.customer,
            "vendor_profile": self.vendor_profile,
            "reason": ReportReason.FAKE_VENDOR,
        }
        defaults.update(kwargs)
        return Report.objects.create(**defaults)


class ReportProductCreateViewTests(ReportViewTestsBase):
    def test_unauthenticated_rejected(self):
        response = self.client.post(
            self.product_url(),
            {"reason": ReportReason.SCAM_OR_FRAUD},
        )

        self.assertIn(
            response.status_code,
            (
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ),
        )

    def test_authenticated_customer_can_report_product(self):
        self.client.force_authenticate(self.customer)

        response = self.client.post(
            self.product_url(),
            {
                "reason": ReportReason.SCAM_OR_FRAUD,
                "description": "This listing appears fraudulent.",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertTrue(response.data["success"])
        self.assertEqual(
            response.data["data"]["target_type"],
            "PRODUCT",
        )
        self.assertEqual(
            response.data["data"]["target_id"],
            str(self.product.id),
        )
        self.assertEqual(
            response.data["data"]["reason"],
            ReportReason.SCAM_OR_FRAUD,
        )

        self.assertTrue(
            Report.objects.filter(
                reporter=self.customer,
                product=self.product,
            ).exists()
        )

    def test_other_reason_requires_description(self):
        self.client.force_authenticate(self.customer)

        response = self.client.post(
            self.product_url(),
            {"reason": ReportReason.OTHER},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(response.data["success"])

    def test_invalid_reason_rejected(self):
        self.client.force_authenticate(self.customer)

        response = self.client.post(
            self.product_url(),
            {"reason": "INVALID_REASON"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_deleted_or_nonexistent_product_returns_404(self):
        self.client.force_authenticate(self.customer)

        response = self.client.post(
            "/api/v1/reports/products/00000000-0000-0000-0000-000000000000/",
            {"reason": ReportReason.SCAM_OR_FRAUD},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


class ReportVendorCreateViewTests(ReportViewTestsBase):
    def test_unauthenticated_rejected(self):
        response = self.client.post(
            self.vendor_url(),
            {"reason": ReportReason.FAKE_VENDOR},
        )

        self.assertIn(
            response.status_code,
            (
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ),
        )

    def test_authenticated_customer_can_report_vendor(self):
        self.client.force_authenticate(self.customer)

        response = self.client.post(
            self.vendor_url(),
            {
                "reason": ReportReason.FAKE_VENDOR,
                "description": "Vendor information appears fraudulent.",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertTrue(response.data["success"])
        self.assertEqual(
            response.data["data"]["target_type"],
            "VENDOR",
        )
        self.assertEqual(
            response.data["data"]["target_id"],
            str(self.vendor_profile.id),
        )

        self.assertTrue(
            Report.objects.filter(
                reporter=self.customer,
                vendor_profile=self.vendor_profile,
            ).exists()
        )

    def test_other_reason_requires_description(self):
        self.client.force_authenticate(self.customer)

        response = self.client.post(
            self.vendor_url(),
            {"reason": ReportReason.OTHER},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_nonexistent_vendor_returns_404(self):
        self.client.force_authenticate(self.customer)

        response = self.client.post(
            "/api/v1/reports/vendors/00000000-0000-0000-0000-000000000000/",
            {"reason": ReportReason.FAKE_VENDOR},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


class MyReportsListViewTests(ReportViewTestsBase):
    def setUp(self):
        super().setUp()

        self.own_report = self.create_product_report()

        self.other_report = self.create_vendor_report(
            reporter=self.other_customer,
        )

    def test_unauthenticated_rejected(self):
        response = self.client.get("/api/v1/reports/mine/")

        self.assertIn(
            response.status_code,
            (
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ),
        )

    def test_customer_only_sees_own_reports(self):
        self.client.force_authenticate(self.customer)

        response = self.client.get("/api/v1/reports/mine/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(response.data["success"])

        returned_ids = {item["id"] for item in response.data["data"]["results"]}

        self.assertIn(str(self.own_report.id), returned_ids)
        self.assertNotIn(str(self.other_report.id), returned_ids)


class ReportAdminListViewTests(ReportViewTestsBase):
    def setUp(self):
        super().setUp()

        self.pending_report = self.create_product_report()

        self.under_review_report = self.create_vendor_report(
            status=ReportStatus.UNDER_REVIEW,
        )

        self.resolved_report = self.create_product_report(
            status=ReportStatus.RESOLVED,
            resolved_by=self.admin,
            resolved_at=timezone.now(),
        )

        self.rejected_report = self.create_vendor_report(
            status=ReportStatus.REJECTED,
        )

    def test_customer_cannot_access_admin_queue(self):
        self.client.force_authenticate(self.customer)

        response = self.client.get("/api/v1/reports/")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_unauthenticated_rejected(self):
        response = self.client.get("/api/v1/reports/")

        self.assertIn(
            response.status_code,
            (
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ),
        )

    def test_staff_admin_can_access_queue(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get("/api/v1/reports/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(response.data["success"])

    def test_superuser_can_access_queue(self):
        self.client.force_authenticate(self.superuser)

        response = self.client.get("/api/v1/reports/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_status_filter_returns_matching_reports(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get(
            "/api/v1/reports/?status=PENDING",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        returned_ids = {item["id"] for item in response.data["data"]["results"]}

        self.assertIn(str(self.pending_report.id), returned_ids)
        self.assertNotIn(str(self.under_review_report.id), returned_ids)
        self.assertNotIn(str(self.resolved_report.id), returned_ids)
        self.assertNotIn(str(self.rejected_report.id), returned_ids)

    def test_invalid_status_filter_returns_400(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get(
            "/api/v1/reports/?status=INVALID",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


class ReportDetailViewTests(ReportViewTestsBase):
    def setUp(self):
        super().setUp()

        self.own_report = self.create_product_report()

        self.other_report = self.create_vendor_report(
            reporter=self.other_customer,
        )

    def test_reporter_can_retrieve_own_report(self):
        self.client.force_authenticate(self.customer)

        response = self.client.get(
            self.report_url(self.own_report),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(response.data["success"])
        self.assertEqual(
            response.data["data"]["id"],
            str(self.own_report.id),
        )

    def test_customer_cannot_retrieve_someone_elses_report(self):
        self.client.force_authenticate(self.customer)

        response = self.client.get(
            self.report_url(self.other_report),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_admin_can_retrieve_any_report(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get(
            self.report_url(self.other_report),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(response.data["success"])

    def test_admin_response_contains_admin_fields(self):
        self.client.force_authenticate(self.admin)

        self.other_report.resolved_by = self.admin
        self.other_report.resolved_at = timezone.now()
        self.other_report.resolution_notes = "Action taken."
        self.other_report.status = ReportStatus.RESOLVED
        self.other_report.save()

        response = self.client.get(
            self.report_url(self.other_report),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        data = response.data["data"]

        self.assertIn("reporter", data)
        self.assertIn("reporter_name", data)
        self.assertIn("resolved_by", data)
        self.assertIn("resolved_by_name", data)
        self.assertIn("resolved_at", data)
        self.assertIn("resolution_notes", data)

    def test_customer_response_does_not_expose_admin_fields(self):
        self.client.force_authenticate(self.customer)

        response = self.client.get(
            self.report_url(self.own_report),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        data = response.data["data"]

        self.assertNotIn("resolved_by", data)
        self.assertNotIn("resolved_by_name", data)
        self.assertNotIn("resolved_at", data)
        self.assertNotIn("resolution_notes", data)

    def test_nonexistent_report_returns_404(self):
        self.client.force_authenticate(self.customer)

        response = self.client.get(
            "/api/v1/reports/00000000-0000-0000-0000-000000000000/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


class ReportUnderReviewViewTests(ReportViewTestsBase):
    def setUp(self):
        super().setUp()
        self.report = self.create_product_report()

    def test_customer_cannot_move_report_under_review(self):
        self.client.force_authenticate(self.customer)

        response = self.client.post(
            self.under_review_url(self.report),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_admin_can_move_pending_report_under_review(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.under_review_url(self.report),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(response.data["success"])

        self.report.refresh_from_db()

        self.assertEqual(
            self.report.status,
            ReportStatus.UNDER_REVIEW,
        )

    def test_admin_cannot_move_closed_report_under_review(self):
        self.report.status = ReportStatus.REJECTED
        self.report.save(update_fields=["status"])

        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.under_review_url(self.report),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )


class ReportResolveViewTests(ReportViewTestsBase):
    def test_customer_cannot_resolve_report(self):
        report = self.create_product_report()

        self.client.force_authenticate(self.customer)

        response = self.client.post(
            self.resolve_url(report),
            {"resolution_notes": "Attempted customer resolution."},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_admin_can_resolve_product_report(self):
        report = self.create_product_report()

        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.resolve_url(report),
            {"resolution_notes": "Listing removed after review."},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(response.data["success"])

        report.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(
            report.status,
            ReportStatus.RESOLVED,
        )
        self.assertEqual(
            report.resolved_by_id,
            self.admin.id,
        )
        self.assertIsNotNone(report.resolved_at)
        self.assertEqual(
            report.resolution_notes,
            "Listing removed after review.",
        )
        self.assertEqual(
            self.product.status,
            ProductStatus.REMOVED_BY_ADMIN,
        )

    def test_admin_can_resolve_vendor_report(self):
        report = self.create_vendor_report()

        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.resolve_url(report),
            {"resolution_notes": "Vendor suspended after review."},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(response.data["success"])

        report.refresh_from_db()
        self.vendor_profile.refresh_from_db()
        self.store.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(
            report.status,
            ReportStatus.RESOLVED,
        )
        self.assertEqual(
            report.resolved_by_id,
            self.admin.id,
        )
        self.assertIsNotNone(report.resolved_at)

        self.assertEqual(
            self.vendor_profile.status,
            VendorStatus.SUSPENDED,
        )
        self.assertFalse(self.store.is_active)
        self.assertEqual(
            self.product.status,
            ProductStatus.HIDDEN_BY_SUSPENSION,
        )

    def test_resolving_already_resolved_report_returns_409(self):
        report = self.create_product_report(
            status=ReportStatus.RESOLVED,
            resolved_by=self.admin,
            resolved_at=timezone.now(),
        )

        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.resolve_url(report),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

    def test_resolving_already_rejected_report_returns_409(self):
        report = self.create_product_report(
            status=ReportStatus.REJECTED,
        )

        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.resolve_url(report),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

    def test_invalid_resolution_notes_are_rejected(self):
        report = self.create_product_report()

        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.resolve_url(report),
            {"resolution_notes": 123},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


class ReportRejectViewTests(ReportViewTestsBase):
    def test_customer_cannot_reject_report(self):
        report = self.create_product_report()

        self.client.force_authenticate(self.customer)

        response = self.client.post(
            self.reject_url(report),
            {"resolution_notes": "Not valid."},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_admin_can_reject_report(self):
        report = self.create_product_report()

        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.reject_url(report),
            {"resolution_notes": "No action warranted."},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(response.data["success"])

        report.refresh_from_db()

        self.assertEqual(
            report.status,
            ReportStatus.REJECTED,
        )
        self.assertEqual(
            report.resolution_notes,
            "No action warranted.",
        )

    def test_reject_does_not_mutate_product(self):
        report = self.create_product_report()

        original_status = self.product.status

        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.reject_url(report),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.status,
            original_status,
        )

    def test_reject_does_not_mutate_vendor(self):
        report = self.create_vendor_report()

        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.reject_url(report),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.vendor_profile.refresh_from_db()
        self.store.refresh_from_db()

        self.assertEqual(
            self.vendor_profile.status,
            VendorStatus.VERIFIED,
        )
        self.assertTrue(self.store.is_active)

    def test_rejecting_already_closed_report_returns_409(self):
        report = self.create_product_report(
            status=ReportStatus.RESOLVED,
            resolved_by=self.admin,
            resolved_at=timezone.now(),
        )

        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.reject_url(report),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

    def test_rejecting_rejected_report_returns_409(self):
        report = self.create_product_report(
            status=ReportStatus.REJECTED,
        )

        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.reject_url(report),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )
