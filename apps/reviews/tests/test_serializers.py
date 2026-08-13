from django.test import TestCase

from apps.chat.models import Conversation, TransactionStatus
from apps.reviews.models import Review
from apps.reviews.serializers import (
    ReviewCreateSerializer,
    ReviewSerializer,
    ReviewUpdateSerializer,
)
from apps.stores.models import Store
from apps.universities.models import University
from apps.users.models import User
from apps.vendors.models import VendorProfile, VendorStatus, VendorType


class ReviewCreateSerializerTests(TestCase):
    def test_valid_payload(self):
        s = ReviewCreateSerializer(data={"rating": 4, "comment": "Nice"})
        self.assertTrue(s.is_valid(), s.errors)

    def test_comment_optional(self):
        s = ReviewCreateSerializer(data={"rating": 4})
        self.assertTrue(s.is_valid(), s.errors)

    def test_rating_below_1_rejected(self):
        s = ReviewCreateSerializer(data={"rating": 0})
        self.assertFalse(s.is_valid())
        self.assertIn("rating", s.errors)

    def test_rating_above_5_rejected(self):
        s = ReviewCreateSerializer(data={"rating": 6})
        self.assertFalse(s.is_valid())
        self.assertIn("rating", s.errors)

    def test_rating_required(self):
        s = ReviewCreateSerializer(data={})
        self.assertFalse(s.is_valid())
        self.assertIn("rating", s.errors)

    def test_store_and_conversation_are_not_accepted_fields(self):
        s = ReviewCreateSerializer(
            data={"rating": 4, "store": "x", "conversation": "y"}
        )
        self.assertTrue(s.is_valid(), s.errors)
        self.assertNotIn("store", s.validated_data)
        self.assertNotIn("conversation", s.validated_data)


class ReviewUpdateSerializerTests(TestCase):
    def test_partial_rating_only(self):
        s = ReviewUpdateSerializer(data={"rating": 2}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)

    def test_partial_comment_only(self):
        s = ReviewUpdateSerializer(data={"comment": "updated"}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)

    def test_empty_payload_rejected(self):
        s = ReviewUpdateSerializer(data={}, partial=True)
        self.assertFalse(s.is_valid())

    def test_rating_out_of_range_rejected(self):
        s = ReviewUpdateSerializer(data={"rating": 9}, partial=True)
        self.assertFalse(s.is_valid())


class ReviewSerializerReadTests(TestCase):
    def setUp(self):
        self.university = University.objects.create(name="U", short_name="U1")
        self.customer = User.objects.create_user(
            email="c@example.com", password="pass1234!", full_name="Cust"
        )
        vendor_user = User.objects.create_user(
            email="v@example.com", password="pass1234!", full_name="Vend"
        )
        self.vendor_profile = VendorProfile.objects.create(
            user=vendor_user,
            university=self.university,
            vendor_type=VendorType.BUSINESS,
            store_name="S",
            phone_number="+2348000000000",
            business_name="B",
            business_address="Addr",
            status=VendorStatus.VERIFIED,
        )
        self.store = Store.objects.create(
            vendor_profile=self.vendor_profile, display_name="S"
        )
        self.conversation = Conversation.objects.create(
            customer=self.customer,
            vendor=self.vendor_profile,
            transaction_status=TransactionStatus.COMPLETED,
        )

    def test_read_only_fields_present(self):
        review = Review.objects.create(
            conversation=self.conversation, store=self.store, rating=5
        )
        data = ReviewSerializer(review).data
        expected_fields = {
            "id",
            "conversation_id",
            "store_id",
            "store_slug",
            "store_display_name",
            "customer_name",
            "rating",
            "comment",
            "is_edited",
            "edited_at",
            "created_at",
            "updated_at",
        }
        self.assertEqual(set(data.keys()), expected_fields)
        self.assertEqual(data["customer_name"], "Cust")
        self.assertEqual(data["store_id"], str(self.store.id))
