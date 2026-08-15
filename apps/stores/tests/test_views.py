from rest_framework import status
from rest_framework.test import APITestCase

from apps.stores.models import Store
from apps.stores.services import StoreService
from apps.universities.models import University
from apps.users.models import User
from apps.vendors.models import VendorProfile, VendorStatus, VendorType


class StoreViewTestsBase(APITestCase):
    def setUp(self):
        self.university = University.objects.create(
            name="University of Ibadan", short_name="UI"
        )

        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="StrongPass123!",
            full_name="Just A Customer",
        )

        self.vendor_user = User.objects.create_user(
            email="vendor@example.com",
            password="StrongPass123!",
            full_name="Vendor One",
        )
        self.vendor_profile = VendorProfile.objects.create(
            user=self.vendor_user,
            university=self.university,
            vendor_type=VendorType.BUSINESS,
            store_name="Vendor Store",
            phone_number="+2348012345678",
            business_name="Vendor Ventures",
            business_address="1 Campus Road",
            status=VendorStatus.VERIFIED,
        )

        self.other_vendor_user = User.objects.create_user(
            email="other-vendor@example.com",
            password="StrongPass123!",
            full_name="Vendor Two",
        )
        self.other_vendor_profile = VendorProfile.objects.create(
            user=self.other_vendor_user,
            university=self.university,
            vendor_type=VendorType.BUSINESS,
            store_name="Other Vendor Store",
            phone_number="+2348099999999",
            business_name="Other Ventures",
            business_address="2 Campus Road",
            status=VendorStatus.VERIFIED,
        )


class StoreCreateViewTests(StoreViewTestsBase):
    url = "/api/v1/stores/"

    def test_anonymous_cannot_create(self):
        response = self.client.post(self.url, {})
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_customer_without_vendor_profile_cannot_create(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.url, {"display_name": "My Store"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_verified_vendor_can_create(self):
        self.client.force_authenticate(self.vendor_user)
        response = self.client.post(self.url, {"display_name": "My Store"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["display_name"], "My Store")

    def test_create_defaults_display_name_when_omitted(self):
        self.client.force_authenticate(self.vendor_user)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["data"]["display_name"], self.vendor_profile.store_name
        )

    def test_vendor_cannot_create_second_store(self):
        self.client.force_authenticate(self.vendor_user)
        self.client.post(self.url, {"display_name": "First"})
        response = self.client.post(self.url, {"display_name": "Second"})
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_created_store_response_envelope_shape(self):
        self.client.force_authenticate(self.vendor_user)
        response = self.client.post(self.url, {"display_name": "My Store"})
        self.assertIn("success", response.data)
        self.assertIn("message", response.data)
        self.assertIn("data", response.data)
        self.assertTrue(response.data["success"])


class StoreRetrieveViewTests(StoreViewTestsBase):
    def setUp(self):
        super().setUp()
        self.store = StoreService.create(
            vendor_profile=self.vendor_profile, display_name="Public Store"
        )

    def test_anonymous_cannot_retrieve(self):
        response = self.client.get(f"/api/v1/stores/{self.store.slug}/")
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_authenticated_customer_can_retrieve_active_store(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(f"/api/v1/stores/{self.store.slug}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["display_name"], "Public Store")

    def test_unknown_slug_returns_404(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get("/api/v1/stores/does-not-exist/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_inactive_store_not_publicly_retrievable(self):
        StoreService.set_active_state(store=self.store, is_active=False)
        self.client.force_authenticate(self.customer)
        response = self.client.get(f"/api/v1/stores/{self.store.slug}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_soft_deleted_store_not_publicly_retrievable(self):
        StoreService.delete(store=self.store)
        self.client.force_authenticate(self.customer)
        response = self.client.get(f"/api/v1/stores/{self.store.slug}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class StoreMeViewTests(StoreViewTestsBase):
    url = "/api/v1/stores/me/"

    def test_anonymous_cannot_access_me(self):
        response = self.client.get(self.url)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_vendor_without_store_gets_404(self):
        self.client.force_authenticate(self.vendor_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_without_vendor_profile_gets_404(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_vendor_can_retrieve_own_store(self):
        store = StoreService.create(
            vendor_profile=self.vendor_profile, display_name="Mine"
        )
        self.client.force_authenticate(self.vendor_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["display_name"], "Mine")
        self.assertEqual(response.data["data"]["slug"], store.slug)

    def test_vendor_sees_own_inactive_store_via_me(self):
        StoreService.create(vendor_profile=self.vendor_profile, display_name="Mine")
        StoreService.set_active_state(store=self.vendor_profile.store, is_active=False)
        self.client.force_authenticate(self.vendor_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["data"]["is_active"])

    def test_vendor_can_update_permitted_fields(self):
        StoreService.create(vendor_profile=self.vendor_profile, display_name="Old Name")
        self.client.force_authenticate(self.vendor_user)
        response = self.client.patch(
            self.url,
            {"display_name": "New Name", "description": "Updated description."},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["display_name"], "New Name")
        self.assertEqual(response.data["data"]["description"], "Updated description.")

    def test_vendor_cannot_modify_protected_fields_via_update(self):
        StoreService.create(vendor_profile=self.vendor_profile, display_name="Old Name")
        self.client.force_authenticate(self.vendor_user)
        original_slug = self.vendor_profile.store.slug
        response = self.client.patch(
            self.url,
            {
                "is_active": False,
                "slug": "hacked-slug",
                "vendor_profile": str(self.other_vendor_profile.pk),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.vendor_profile.store.refresh_from_db()
        self.assertTrue(self.vendor_profile.store.is_active)
        self.assertEqual(self.vendor_profile.store.slug, original_slug)
        self.assertEqual(
            self.vendor_profile.store.vendor_profile_id, self.vendor_profile.pk
        )

    def test_vendor_can_delete_own_store(self):
        StoreService.create(vendor_profile=self.vendor_profile, display_name="Old Name")
        self.client.force_authenticate(self.vendor_user)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.vendor_profile.refresh_from_db()
        store = Store.objects.get(vendor_profile=self.vendor_profile)
        self.assertTrue(store.is_deleted)

    def test_me_returns_404_after_deletion(self):
        StoreService.create(vendor_profile=self.vendor_profile, display_name="Old Name")
        self.client.force_authenticate(self.vendor_user)
        self.client.delete(self.url)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_vendor_cannot_edit_another_vendors_store_via_me(self):
        StoreService.create(
            vendor_profile=self.other_vendor_profile, display_name="Not Yours"
        )
        self.client.force_authenticate(self.vendor_user)
        response = self.client.get(self.url)
        # request.user (vendor_user) has no store of their own — /me/ never
        # consults any client-supplied identifier, so there is no path by
        # which they could reach the other vendor's store through this
        # endpoint.
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
