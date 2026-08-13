from django.test import TestCase

from apps.chat.models import Conversation, TransactionStatus
from apps.common.exceptions import (
    ApplicationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from apps.reviews.services import ReviewService
from apps.stores.models import Store
from apps.universities.models import University
from apps.users.models import User
from apps.vendors.models import VendorProfile, VendorStatus, VendorType


class ReviewServiceTestsBase(TestCase):
    def setUp(self):
        self.university = University.objects.create(
            name="Test University",
            short_name="TU",
        )
        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="pass1234!",
            full_name="Cust Omer",
        )
        self.other_customer = User.objects.create_user(
            email="other@example.com",
            password="pass1234!",
            full_name="Other One",
        )
        vendor_user = User.objects.create_user(
            email="vendor@example.com",
            password="pass1234!",
            full_name="Ven Dor",
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
            vendor_profile=self.vendor_profile,
            display_name="Vendor Store",
        )
        self.completed_conversation = Conversation.objects.create(
            customer=self.customer,
            vendor=self.vendor_profile,
            transaction_status=TransactionStatus.COMPLETED,
        )
        self.ongoing_conversation = Conversation.objects.create(
            customer=self.customer,
            vendor=self.vendor_profile,
        )


class ReviewServiceCreateTests(ReviewServiceTestsBase):
    def test_creates_review_for_completed_conversation(self):
        review = ReviewService.create(
            conversation=self.completed_conversation,
            customer=self.customer,
            rating=5,
            comment="Great!",
        )
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, "Great!")

    def test_store_is_derived_from_conversation_vendor(self):
        review = ReviewService.create(
            conversation=self.completed_conversation,
            customer=self.customer,
            rating=4,
        )
        self.assertEqual(review.store_id, self.store.id)

    def test_rejects_rating_below_minimum(self):
        with self.assertRaises(ApplicationError):
            ReviewService.create(
                conversation=self.completed_conversation,
                customer=self.customer,
                rating=0,
            )

    def test_rejects_rating_above_maximum(self):
        with self.assertRaises(ApplicationError):
            ReviewService.create(
                conversation=self.completed_conversation,
                customer=self.customer,
                rating=6,
            )

    def test_rejects_boolean_rating(self):
        with self.assertRaises(ApplicationError):
            ReviewService.create(
                conversation=self.completed_conversation,
                customer=self.customer,
                rating=True,
            )

    def test_rejects_ongoing_conversation(self):
        with self.assertRaises(ConflictError):
            ReviewService.create(
                conversation=self.ongoing_conversation,
                customer=self.customer,
                rating=4,
            )

    def test_rejects_non_owning_customer(self):
        with self.assertRaises(PermissionDeniedError):
            ReviewService.create(
                conversation=self.completed_conversation,
                customer=self.other_customer,
                rating=4,
            )

    def test_rejects_duplicate_review(self):
        ReviewService.create(
            conversation=self.completed_conversation,
            customer=self.customer,
            rating=5,
        )

        with self.assertRaises(ConflictError):
            ReviewService.create(
                conversation=self.completed_conversation,
                customer=self.customer,
                rating=3,
            )

    def test_review_creation_does_not_mutate_transaction_status(self):
        ReviewService.create(
            conversation=self.completed_conversation,
            customer=self.customer,
            rating=5,
        )
        self.completed_conversation.refresh_from_db()

        self.assertEqual(
            self.completed_conversation.transaction_status,
            TransactionStatus.COMPLETED,
        )

    def test_rejects_when_vendor_has_no_store(self):
        vendor_user2 = User.objects.create_user(
            email="vendor2@example.com",
            password="pass1234!",
            full_name="Ven Dor2",
        )
        storeless_vendor = VendorProfile.objects.create(
            user=vendor_user2,
            university=self.university,
            vendor_type=VendorType.BUSINESS,
            store_name="Storeless",
            phone_number="+2348000000001",
            business_name="No Store Biz",
            business_address="2 Campus Rd",
            status=VendorStatus.VERIFIED,
        )
        conv = Conversation.objects.create(
            customer=self.customer,
            vendor=storeless_vendor,
            transaction_status=TransactionStatus.COMPLETED,
        )

        with self.assertRaises(NotFoundError):
            ReviewService.create(
                conversation=conv,
                customer=self.customer,
                rating=4,
            )


class ReviewServiceUpdateTests(ReviewServiceTestsBase):
    def setUp(self):
        super().setUp()
        self.review = ReviewService.create(
            conversation=self.completed_conversation,
            customer=self.customer,
            rating=3,
            comment="ok",
        )

    def test_owner_can_edit_rating_and_comment(self):
        updated = ReviewService.update(
            review=self.review,
            actor=self.customer,
            rating=5,
            comment="Amazing",
        )
        self.assertEqual(updated.rating, 5)
        self.assertEqual(updated.comment, "Amazing")

    def test_edit_sets_edited_at(self):
        self.assertIsNone(self.review.edited_at)

        updated = ReviewService.update(
            review=self.review,
            actor=self.customer,
            rating=4,
        )

        self.assertIsNotNone(updated.edited_at)

    def test_partial_edit_only_rating_leaves_comment_untouched(self):
        updated = ReviewService.update(
            review=self.review,
            actor=self.customer,
            rating=1,
        )
        self.assertEqual(updated.rating, 1)
        self.assertEqual(updated.comment, "ok")

    def test_partial_edit_only_comment_leaves_rating_untouched(self):
        updated = ReviewService.update(
            review=self.review,
            actor=self.customer,
            comment="revised",
        )
        self.assertEqual(updated.rating, 3)
        self.assertEqual(updated.comment, "revised")

    def test_rejects_rating_below_minimum(self):
        with self.assertRaises(ApplicationError):
            ReviewService.update(
                review=self.review,
                actor=self.customer,
                rating=0,
            )

    def test_rejects_rating_above_maximum(self):
        with self.assertRaises(ApplicationError):
            ReviewService.update(
                review=self.review,
                actor=self.customer,
                rating=6,
            )

    def test_rejects_boolean_rating(self):
        with self.assertRaises(ApplicationError):
            ReviewService.update(
                review=self.review,
                actor=self.customer,
                rating=True,
            )

    def test_rejects_edit_by_non_owner(self):
        with self.assertRaises(PermissionDeniedError):
            ReviewService.update(
                review=self.review,
                actor=self.other_customer,
                rating=1,
            )

    def test_update_signature_has_no_store_parameter(self):
        # Structural proof that Store cannot be client-controlled via edit.
        with self.assertRaises(TypeError):
            ReviewService.update(
                review=self.review,
                actor=self.customer,
                store=object(),
            )


class ReviewServiceGetForConversationTests(ReviewServiceTestsBase):
    def test_returns_review_when_present(self):
        review = ReviewService.create(
            conversation=self.completed_conversation,
            customer=self.customer,
            rating=5,
        )
        found = ReviewService.get_for_conversation(
            conversation=self.completed_conversation,
        )
        self.assertEqual(found.id, review.id)

    def test_raises_not_found_when_absent(self):
        with self.assertRaises(NotFoundError):
            ReviewService.get_for_conversation(
                conversation=self.ongoing_conversation,
            )
