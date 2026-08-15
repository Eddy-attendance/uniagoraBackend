from django.test import TestCase

from apps.common.exceptions import ConflictError
from apps.stores.models import Store
from apps.stores.services import StoreService
from apps.universities.models import University
from apps.users.models import User
from apps.vendors.models import VendorProfile, VendorStatus, VendorType


class StoreServiceTestsBase(TestCase):
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
            vendor_type=VendorType.STUDENT,
            store_name="Vendor's Corner",
            phone_number="+2348012345678",
            matric_number="UI/2020/001",
            department="Computer Science",
            level="300",
            status=VendorStatus.VERIFIED,
        )


class StoreServiceCreateTests(StoreServiceTestsBase):
    def test_create_defaults_display_name_from_vendor_store_name(self):
        store = StoreService.create(vendor_profile=self.vendor_profile)
        self.assertEqual(store.display_name, "Vendor's Corner")

    def test_create_defaults_contact_phone_from_vendor_phone(self):
        store = StoreService.create(vendor_profile=self.vendor_profile)
        self.assertEqual(store.contact_phone, "+2348012345678")

    def test_create_accepts_explicit_overrides(self):
        store = StoreService.create(
            vendor_profile=self.vendor_profile,
            display_name="Custom Storefront",
            description="We sell everything.",
            contact_phone="+2348099999999",
        )
        self.assertEqual(store.display_name, "Custom Storefront")
        self.assertEqual(store.description, "We sell everything.")
        self.assertEqual(store.contact_phone, "+2348099999999")

    def test_create_defaults_is_active_true(self):
        store = StoreService.create(vendor_profile=self.vendor_profile)
        self.assertTrue(store.is_active)

    def test_create_raises_conflict_for_second_store(self):
        StoreService.create(vendor_profile=self.vendor_profile)
        with self.assertRaises(ConflictError):
            StoreService.create(vendor_profile=self.vendor_profile)

    def test_create_does_not_persist_second_store_after_conflict(self):
        StoreService.create(vendor_profile=self.vendor_profile)
        try:
            StoreService.create(vendor_profile=self.vendor_profile)
        except ConflictError:
            pass
        self.assertEqual(
            Store.objects.filter(vendor_profile=self.vendor_profile).count(), 1
        )


class StoreServiceUpdateTests(StoreServiceTestsBase):
    def setUp(self):
        super().setUp()
        self.store = StoreService.create(vendor_profile=self.vendor_profile)

    def test_update_changes_only_provided_fields(self):
        original_contact_phone = self.store.contact_phone
        updated = StoreService.update(store=self.store, display_name="New Name")
        self.assertEqual(updated.display_name, "New Name")
        self.assertEqual(updated.contact_phone, original_contact_phone)

    def test_update_with_no_arguments_is_a_no_op(self):
        original_updated_at = self.store.updated_at
        StoreService.update(store=self.store)
        self.store.refresh_from_db()
        self.assertEqual(self.store.updated_at, original_updated_at)

    def test_update_can_explicitly_clear_nullable_description(self):
        StoreService.update(store=self.store, description="Some description")
        updated = StoreService.update(store=self.store, description=None)
        self.assertIsNone(updated.description)

    def test_update_never_touches_slug(self):
        original_slug = self.store.slug
        StoreService.update(store=self.store, display_name="Totally Different Name")
        self.store.refresh_from_db()
        self.assertEqual(self.store.slug, original_slug)

    def test_update_never_touches_is_active(self):
        StoreService.update(store=self.store, display_name="Whatever")
        self.store.refresh_from_db()
        self.assertTrue(self.store.is_active)


class StoreServiceDeleteTests(StoreServiceTestsBase):
    def setUp(self):
        super().setUp()
        self.store = StoreService.create(vendor_profile=self.vendor_profile)

    def test_delete_soft_deletes(self):
        StoreService.delete(store=self.store)
        self.store.refresh_from_db()
        self.assertTrue(self.store.is_deleted)
        self.assertTrue(Store.objects.filter(pk=self.store.pk).exists())


class StoreServiceSetActiveStateTests(StoreServiceTestsBase):
    def setUp(self):
        super().setUp()
        self.store = StoreService.create(vendor_profile=self.vendor_profile)

    def test_set_active_state_false(self):
        StoreService.set_active_state(store=self.store, is_active=False)
        self.store.refresh_from_db()
        self.assertFalse(self.store.is_active)

    def test_set_active_state_true_after_false(self):
        StoreService.set_active_state(store=self.store, is_active=False)
        StoreService.set_active_state(store=self.store, is_active=True)
        self.store.refresh_from_db()
        self.assertTrue(self.store.is_active)

    def test_set_active_state_is_idempotent_noop_when_unchanged(self):
        original_updated_at = self.store.updated_at
        StoreService.set_active_state(store=self.store, is_active=True)
        self.store.refresh_from_db()
        self.assertEqual(self.store.updated_at, original_updated_at)
