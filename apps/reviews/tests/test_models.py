from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.chat.models import Conversation, TransactionStatus
from apps.reviews.models import Review
from apps.stores.models import Store
from apps.universities.models import University
from apps.users.models import User
from apps.vendors.models import VendorProfile, VendorStatus, VendorType


class ReviewModelTests(TestCase):
    def setUp(self):
        self.university = University.objects.create(
            name="Test University", short_name="TU"
        )
        self.customer = User.objects.create_user(
            email="customer@example.com", password="pass1234!", full_name="Cust Omer"
        )
        vendor_user = User.objects.create_user(
            email="vendor@example.com", password="pass1234!", full_name="Ven Dor"
        )
        self.vendor_profile = VendorProfile.objects.create(
            user=vendor_user,
            university=self.university,
            vendor_type=VendorType.BUSINESS,
            store_name="Vendor Store",
            phone_number="+2348000000000",
            business_name="Vendor Biz",
            business_address="1 Campus Rd",
            status=VendorStatus.VERIFIED,
        )
        self.store = Store.objects.create(
            vendor_profile=self.vendor_profile, display_name="Vendor Store"
        )
        self.conversation = Conversation.objects.create(
            customer=self.customer,
            vendor=self.vendor_profile,
            transaction_status=TransactionStatus.COMPLETED,
        )

    def test_str_returns_rating_and_store(self):
        review = Review.objects.create(
            conversation=self.conversation, store=self.store, rating=4
        )
        self.assertEqual(str(review), f"4★ for {self.store.display_name}")

    def test_is_edited_false_when_never_edited(self):
        review = Review.objects.create(
            conversation=self.conversation, store=self.store, rating=5
        )
        self.assertFalse(review.is_edited)

    def test_is_edited_true_once_edited_at_set(self):
        review = Review.objects.create(
            conversation=self.conversation, store=self.store, rating=5
        )
        review.edited_at = timezone.now()
        review.save(update_fields=["edited_at"])
        self.assertTrue(review.is_edited)

    def test_one_review_per_conversation_db_constraint(self):
        Review.objects.create(
            conversation=self.conversation, store=self.store, rating=3
        )
        with self.assertRaises(IntegrityError):
            Review.objects.create(
                conversation=self.conversation, store=self.store, rating=2
            )

    def test_rating_check_constraint_rejects_zero(self):
        review = Review(conversation=self.conversation, store=self.store, rating=0)
        with self.assertRaises(  # noqa: B017
            Exception
        ):
            review.full_clean()

    def test_rating_check_constraint_rejects_six(self):
        review = Review(conversation=self.conversation, store=self.store, rating=6)
        with self.assertRaises(  # noqa: B017
            Exception
        ):
            review.full_clean()

    def test_comment_optional(self):
        review = Review.objects.create(
            conversation=self.conversation, store=self.store, rating=5, comment=None
        )
        self.assertIsNone(review.comment)

    def test_soft_delete_regression(self):
        review = Review.objects.create(
            conversation=self.conversation, store=self.store, rating=5
        )
        review.delete()
        self.assertTrue(Review.objects.filter(pk=review.pk).exists())
        self.assertFalse(Review.objects.alive().filter(pk=review.pk).exists())

    def test_conversation_protect_blocks_hard_delete(self):
        Review.objects.create(
            conversation=self.conversation, store=self.store, rating=5
        )
        with self.assertRaises(IntegrityError):
            self.conversation.delete(hard=True)
