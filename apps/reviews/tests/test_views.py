from rest_framework import status
from rest_framework.test import APITestCase

from apps.chat.models import Conversation, TransactionStatus
from apps.stores.models import Store
from apps.universities.models import University
from apps.users.models import User
from apps.vendors.models import VendorProfile, VendorStatus, VendorType


class ReviewViewTestsBase(APITestCase):
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

        self.vendor_user = User.objects.create_user(
            email="vendor@example.com",
            password="pass1234!",
            full_name="Ven Dor",
        )

        self.vendor_profile = VendorProfile.objects.create(
            user=self.vendor_user,
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
            customer=self.other_customer,
            vendor=self.vendor_profile,
        )


class ConversationReviewCreateViewTests(ReviewViewTestsBase):
    def url(self, conversation_id):
        return f"/api/v1/reviews/conversations/{conversation_id}/"

    def test_unauthenticated_rejected(self):
        response = self.client.post(
            self.url(self.completed_conversation.id),
            {"rating": 5},
        )

        self.assertIn(
            response.status_code,
            (
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ),
        )

    def test_customer_creates_review_successfully(self):
        self.client.force_authenticate(self.customer)

        response = self.client.post(
            self.url(self.completed_conversation.id),
            {
                "rating": 5,
                "comment": "Great vendor",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["rating"], 5)

    def test_non_owning_customer_rejected(self):
        self.client.force_authenticate(self.other_customer)

        response = self.client.post(
            self.url(self.completed_conversation.id),
            {"rating": 5},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertFalse(response.data["success"])

    def test_ongoing_conversation_rejected(self):
        self.client.force_authenticate(self.other_customer)

        response = self.client.post(
            self.url(self.ongoing_conversation.id),
            {"rating": 5},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

    def test_duplicate_review_rejected(self):
        self.client.force_authenticate(self.customer)

        self.client.post(
            self.url(self.completed_conversation.id),
            {"rating": 5},
        )

        response = self.client.post(
            self.url(self.completed_conversation.id),
            {"rating": 3},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

    def test_rating_out_of_range_rejected(self):
        self.client.force_authenticate(self.customer)

        response = self.client.post(
            self.url(self.completed_conversation.id),
            {"rating": 6},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


class ConversationReviewRetrieveViewTests(ReviewViewTestsBase):
    def setUp(self):
        super().setUp()

        self.client.force_authenticate(self.customer)

        self.client.post(
            f"/api/v1/reviews/conversations/{self.completed_conversation.id}/",
            {
                "rating": 4,
                "comment": "Solid",
            },
        )

        self.client.force_authenticate(None)

    def test_customer_participant_can_retrieve(self):
        self.client.force_authenticate(self.customer)

        response = self.client.get(
            f"/api/v1/reviews/conversations/{self.completed_conversation.id}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["data"]["rating"],
            4,
        )

    def test_vendor_participant_can_retrieve(self):
        self.client.force_authenticate(self.vendor_user)

        response = self.client.get(
            f"/api/v1/reviews/conversations/{self.completed_conversation.id}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_non_participant_rejected(self):
        self.client.force_authenticate(self.other_customer)

        response = self.client.get(
            f"/api/v1/reviews/conversations/{self.completed_conversation.id}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_missing_review_returns_404(self):
        self.client.force_authenticate(self.other_customer)

        response = self.client.get(
            f"/api/v1/reviews/conversations/{self.ongoing_conversation.id}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


class ReviewDetailViewTests(ReviewViewTestsBase):
    def setUp(self):
        super().setUp()

        self.client.force_authenticate(self.customer)

        create_response = self.client.post(
            f"/api/v1/reviews/conversations/{self.completed_conversation.id}/",
            {
                "rating": 3,
                "comment": "ok",
            },
        )

        self.review_id = create_response.data["data"]["id"]

        self.client.force_authenticate(None)

    def test_any_authenticated_user_can_retrieve(self):
        self.client.force_authenticate(self.other_customer)

        response = self.client.get(
            f"/api/v1/reviews/{self.review_id}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_owner_can_edit(self):
        self.client.force_authenticate(self.customer)

        response = self.client.patch(
            f"/api/v1/reviews/{self.review_id}/",
            {
                "rating": 5,
                "comment": "Even better",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["data"]["rating"],
            5,
        )
        self.assertIsNotNone(
            response.data["data"]["edited_at"],
        )

    def test_non_owner_rejected(self):
        self.client.force_authenticate(self.other_customer)

        response = self.client.patch(
            f"/api/v1/reviews/{self.review_id}/",
            {"rating": 1},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_empty_patch_rejected(self):
        self.client.force_authenticate(self.customer)

        response = self.client.patch(
            f"/api/v1/reviews/{self.review_id}/",
            {},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_unauthenticated_rejected(self):
        response = self.client.get(
            f"/api/v1/reviews/{self.review_id}/",
        )

        self.assertIn(
            response.status_code,
            (
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ),
        )


class StoreReviewListViewTests(ReviewViewTestsBase):
    def setUp(self):
        super().setUp()

        self.client.force_authenticate(self.customer)

        self.client.post(
            f"/api/v1/reviews/conversations/{self.completed_conversation.id}/",
            {
                "rating": 5,
                "comment": "Excellent",
            },
        )

        self.client.force_authenticate(None)

    def test_lists_store_reviews_paginated_envelope(self):
        self.client.force_authenticate(self.other_customer)

        response = self.client.get(
            f"/api/v1/reviews/stores/{self.store.slug}/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(response.data["success"])
        self.assertEqual(
            response.data["data"]["count"],
            1,
        )
        self.assertEqual(
            len(response.data["data"]["results"]),
            1,
        )

    def test_unknown_store_returns_404(self):
        self.client.force_authenticate(self.other_customer)

        response = self.client.get(
            "/api/v1/reviews/stores/does-not-exist/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_unauthenticated_rejected(self):
        response = self.client.get(
            f"/api/v1/reviews/stores/{self.store.slug}/",
        )

        self.assertIn(
            response.status_code,
            (
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ),
        )
