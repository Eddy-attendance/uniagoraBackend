from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.stores.models import Store
from apps.universities.models import University
from apps.users.models import User
from apps.vendors.models import VendorProfile, VendorStatus, VendorType


class StoreModelTests(TestCase):
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
            store_name="Vendor One Store",
            phone_number="+2348012345678",
            business_name="Vendor One Ventures",
            business_address="1 Campus Road",
            status=VendorStatus.VERIFIED,
        )

    def test_str_returns_display_name(self):
        store = Store.objects.create(
            vendor_profile=self.vendor_profile, display_name="Cool Store"
        )
        self.assertEqual(str(store), "Cool Store")

    def test_slug_auto_generated_from_display_name(self):
        store = Store.objects.create(
            vendor_profile=self.vendor_profile, display_name="Cool Store"
        )
        self.assertTrue(store.slug)
        self.assertIn("cool-store", store.slug)

    def test_slug_not_regenerated_on_rename(self):
        store = Store.objects.create(
            vendor_profile=self.vendor_profile, display_name="Cool Store"
        )
        original_slug = store.slug
        store.display_name = "Renamed Store"
        store.save()
        store.refresh_from_db()
        self.assertEqual(store.slug, original_slug)

    def test_is_active_defaults_true(self):
        store = Store.objects.create(
            vendor_profile=self.vendor_profile, display_name="Cool Store"
        )
        self.assertTrue(store.is_active)

    def test_one_store_per_vendor_profile_enforced_at_db_level(self):
        Store.objects.create(vendor_profile=self.vendor_profile, display_name="First")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Store.objects.create(
                    vendor_profile=self.vendor_profile, display_name="Second"
                )

    def test_soft_delete_retains_row_and_is_excluded_from_alive(self):
        store = Store.objects.create(
            vendor_profile=self.vendor_profile, display_name="Cool Store"
        )
        store.delete()

        self.assertTrue(Store.objects.filter(pk=store.pk).exists())
        self.assertFalse(Store.objects.alive().filter(pk=store.pk).exists())
        self.assertTrue(Store.objects.dead().filter(pk=store.pk).exists())

    def test_unfiltered_default_manager_includes_soft_deleted(self):
        store = Store.objects.create(
            vendor_profile=self.vendor_profile, display_name="Cool Store"
        )
        store.delete()
        self.assertIn(store, Store.objects.all())

    def test_restore_reverses_soft_delete(self):
        store = Store.objects.create(
            vendor_profile=self.vendor_profile, display_name="Cool Store"
        )
        store.delete()
        store.restore()
        self.assertTrue(Store.objects.alive().filter(pk=store.pk).exists())

    def test_reverse_accessor_on_vendor_profile(self):
        store = Store.objects.create(
            vendor_profile=self.vendor_profile, display_name="Cool Store"
        )
        self.vendor_profile.refresh_from_db()
        self.assertEqual(self.vendor_profile.store, store)

    def test_hard_delete_of_vendor_profile_cascades_to_store(self):
        store = Store.objects.create(
            vendor_profile=self.vendor_profile, display_name="Cool Store"
        )
        store_pk = store.pk
        self.vendor_profile.delete(hard=True)
        self.assertFalse(Store.objects.filter(pk=store_pk).exists())
