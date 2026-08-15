from django.test import TestCase

from apps.stores.serializers import StoreSerializer, StoreWriteSerializer
from apps.stores.services import StoreService
from apps.universities.models import University
from apps.users.models import User
from apps.vendors.models import VendorProfile, VendorStatus, VendorType


class StoreSerializerTests(TestCase):
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

    def test_read_serializer_field_set(self):
        data = StoreSerializer(self.store).data
        expected_fields = {
            "id",
            "display_name",
            "slug",
            "description",
            "contact_phone",
            "is_active",
            "vendor_type",
            "is_verified",
            "created_at",
            "updated_at",
        }
        self.assertEqual(set(data.keys()), expected_fields)

    def test_read_serializer_exposes_verification_badge(self):
        data = StoreSerializer(self.store).data
        self.assertEqual(data["vendor_type"], VendorType.BUSINESS)
        self.assertTrue(data["is_verified"])

    def test_read_serializer_does_not_expose_sensitive_vendor_fields(self):
        data = StoreSerializer(self.store).data
        for sensitive_field in (
            "matric_number",
            "business_address",
            "business_name",
            "vendor_profile",
        ):
            self.assertNotIn(sensitive_field, data)


class StoreWriteSerializerTests(TestCase):
    def test_accepts_valid_payload(self):
        serializer = StoreWriteSerializer(
            data={
                "display_name": "New Store",
                "description": "A great store.",
                "contact_phone": "+2348011112222",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["display_name"], "New Store")

    def test_empty_payload_is_valid_for_partial_update(self):
        serializer = StoreWriteSerializer(data={}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data, {})

    def test_display_name_blank_is_rejected(self):
        serializer = StoreWriteSerializer(data={"display_name": ""})
        self.assertFalse(serializer.is_valid())
        self.assertIn("display_name", serializer.errors)

    def test_invalid_contact_phone_is_rejected(self):
        serializer = StoreWriteSerializer(data={"contact_phone": "not-a-phone-number"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("contact_phone", serializer.errors)

    def test_protected_fields_are_silently_ignored(self):
        serializer = StoreWriteSerializer(
            data={
                "display_name": "New Store",
                "is_active": False,
                "slug": "hacked-slug",
                "vendor_profile": "11111111-1111-1111-1111-111111111111",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("is_active", serializer.validated_data)
        self.assertNotIn("slug", serializer.validated_data)
        self.assertNotIn("vendor_profile", serializer.validated_data)
