from django.test import TestCase

from apps.stores.services import StoreService
from apps.universities.models import University
from apps.users.models import User
from apps.vendors.models import VendorProfile, VendorStatus, VendorType
from apps.vendors.services import VendorSuspensionService


class VendorSuspensionStoreCascadeTests(TestCase):
    def setUp(self):
        self.university = University.objects.create(
            name="University of Ibadan", short_name="UI"
        )
        self.user = User.objects.create_user(
            email="vendor@example.com",
            password="StrongPass123!",
            full_name="Vendor One",
        )
        self.vendor_profile = VendorProfile.objects.create(
            user=self.user,
            university=self.university,
            vendor_type=VendorType.BUSINESS,
            store_name="Vendor Store",
            phone_number="+2348012345678",
            business_name="Vendor Ventures",
            business_address="1 Campus Road",
            status=VendorStatus.VERIFIED,
        )
        self.store = StoreService.create(vendor_profile=self.vendor_profile)

    def test_suspend_makes_store_inactive(self):
        VendorSuspensionService.suspend(vendor_profile=self.vendor_profile)
        self.store.refresh_from_db()
        self.assertFalse(self.store.is_active)

    def test_reinstate_makes_store_active_again(self):
        VendorSuspensionService.suspend(vendor_profile=self.vendor_profile)
        VendorSuspensionService.reinstate(vendor_profile=self.vendor_profile)
        self.store.refresh_from_db()
        self.assertTrue(self.store.is_active)

    def test_suspend_does_not_error_when_vendor_has_no_store_yet(self):
        # A verified vendor who has not yet created a store must still be
        # suspendable without the cascade raising.
        other_user = User.objects.create_user(
            email="no-store-vendor@example.com",
            password="StrongPass123!",
            full_name="No Store Vendor",
        )
        vendor_without_store = VendorProfile.objects.create(
            user=other_user,
            university=self.university,
            vendor_type=VendorType.BUSINESS,
            store_name="No Store Yet",
            phone_number="+2348011110000",
            business_name="No Store Ventures",
            business_address="3 Campus Road",
            status=VendorStatus.VERIFIED,
        )
        # Should not raise.
        VendorSuspensionService.suspend(vendor_profile=vendor_without_store)
