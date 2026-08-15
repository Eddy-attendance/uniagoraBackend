from unittest.mock import patch

from rest_framework import status

from apps.universities.models import University
from apps.vendors.models import VendorProfile, VendorStatus, VendorType

from .base import AdminAPITestCase


class AdminVendorViewTests(AdminAPITestCase):
    def setUp(self):
        super().setUp()
        self.university = University.objects.create(
            name="Test University", short_name="TU"
        )
        self.vendor_user = type(self.admin).objects.create_user(
            email="vendor@uniagora.test",
            password="StrongPass123!",
            full_name="Vendor One",
        )
        self.vendor = VendorProfile.objects.create(
            user=self.vendor_user,
            university=self.university,
            vendor_type=VendorType.BUSINESS,
            store_name="Test Store",
            phone_number="+2348000000000",
            business_name="Test Biz",
            business_address="1 Campus Rd",
            status=VendorStatus.VERIFIED,
        )

    def test_non_admin_rejected(self):
        self.client.force_authenticate(self.customer)
        r = self.client.get("/api/v1/admin/vendors/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_rejected(self):
        r = self.client.get("/api/v1/admin/vendors/")
        self.assertIn(r.status_code, (401, 403))

    def test_admin_lists_vendors(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get("/api/v1/admin/vendors/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_status_filter(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get("/api/v1/admin/vendors/?status=SUSPENDED")
        self.assertEqual(r.json()["data"]["count"], 0)

    def test_unknown_vendor_404(self):
        import uuid

        self.client.force_authenticate(self.admin)
        r = self.client.get(f"/api/v1/admin/vendors/{uuid.uuid4()}/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_suspend_delegates_to_vendor_service(self):
        self.client.force_authenticate(self.admin)
        r = self.client.post(f"/api/v1/admin/vendors/{self.vendor.id}/suspend/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.status, VendorStatus.SUSPENDED)

    def test_suspend_already_suspended_conflicts(self):
        self.client.force_authenticate(self.admin)
        url = f"/api/v1/admin/vendors/{self.vendor.id}/suspend/"
        self.client.post(url)
        r = self.client.post(url)
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

    def test_reinstate_delegates_to_vendor_service(self):
        self.client.force_authenticate(self.admin)
        self.client.post(f"/api/v1/admin/vendors/{self.vendor.id}/suspend/")
        r = self.client.post(f"/api/v1/admin/vendors/{self.vendor.id}/reinstate/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.status, VendorStatus.VERIFIED)

    def test_admin_dashboard_never_sets_vendor_status_directly(self):
        with patch(
            "apps.admin_dashboard.services.VendorSuspensionService.suspend"
        ) as mock_suspend:
            mock_suspend.return_value = self.vendor
            self.client.force_authenticate(self.admin)
            self.client.post(f"/api/v1/admin/vendors/{self.vendor.id}/suspend/")
        mock_suspend.assert_called_once_with(vendor_profile=self.vendor)
