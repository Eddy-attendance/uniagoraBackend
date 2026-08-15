from uuid import UUID

from rest_framework import status
from rest_framework.test import APITestCase

from apps.chat.models import Conversation, Message, TransactionStatus
from apps.chat.tests.helpers import make_product, make_store, make_user, make_vendor


class ConversationCreateViewTests(APITestCase):
    def setUp(self):
        self.vendor = make_vendor()
        self.store = make_store(vendor_profile=self.vendor)
        self.customer = make_user(email="customer@example.com")
        self.url = "/api/v1/conversations/"

    def test_requires_authentication(self):
        response = self.client.post(self.url, {"vendor": str(self.vendor.id)})
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_customer_can_create_conversation(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.url, {"vendor": str(self.vendor.id)})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["vendor"], UUID(str(self.vendor.id)))
        self.assertEqual(response.data["data"]["unread_count"], 0)

    def test_repeated_create_resolves_idempotently_with_200(self):
        self.client.force_authenticate(self.customer)
        first = self.client.post(self.url, {"vendor": str(self.vendor.id)})
        second = self.client.post(self.url, {"vendor": str(self.vendor.id)})

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["data"]["id"], second.data["data"]["id"])
        self.assertEqual(
            Conversation.objects.filter(
                customer=self.customer, vendor=self.vendor, product=None
            ).count(),
            1,
        )

    def test_vendor_messaging_own_store_is_rejected(self):
        self.client.force_authenticate(self.vendor.user)
        response = self.client.post(self.url, {"vendor": str(self.vendor.id)})
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_create_with_product_success(self):
        product = make_product(store=self.store)
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.url, {"vendor": str(self.vendor.id), "product": str(product.id)}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["product"], UUID(str(product.id)))

    def test_response_envelope_shape(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.url, {"vendor": str(self.vendor.id)})
        self.assertIn("success", response.data)
        self.assertIn("data", response.data)
        self.assertTrue(response.data["success"])


class ConversationListRetrieveViewTests(APITestCase):
    def setUp(self):
        self.vendor = make_vendor()
        self.customer = make_user(email="customer@example.com")
        self.stranger = make_user(email="stranger@example.com")
        self.conversation = Conversation.objects.create(
            customer=self.customer, vendor=self.vendor
        )
        self.list_url = "/api/v1/conversations/"
        self.detail_url = f"/api/v1/conversations/{self.conversation.id}/"

    def test_list_returns_only_own_conversations_for_customer(self):
        other_customer = make_user(email="other@example.com")
        Conversation.objects.create(customer=other_customer, vendor=self.vendor)

        self.client.force_authenticate(self.customer)
        response = self.client.get(self.list_url)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.conversation.id))

    def test_list_includes_conversations_from_vendor_side(self):
        self.client.force_authenticate(self.vendor.user)
        response = self.client.get(self.list_url)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)

    def test_participant_can_retrieve(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_participant_cannot_retrieve(self):
        self.client.force_authenticate(self.stranger)
        response = self.client.get(self.detail_url)
        self.assertIn(
            response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
        )

    def test_list_unread_count_excludes_own_messages(self):
        Message.objects.create(
            conversation=self.conversation,
            sender=self.customer,
            body="from me",
        )
        Message.objects.create(
            conversation=self.conversation,
            sender=self.vendor.user,
            body="from vendor",
        )
        self.client.force_authenticate(self.customer)
        response = self.client.get(self.list_url)
        result = response.data["data"]["results"][0]
        self.assertEqual(result["unread_count"], 1)


class ConversationMessagesViewTests(APITestCase):
    def setUp(self):
        self.vendor = make_vendor()
        self.customer = make_user(email="customer@example.com")
        self.stranger = make_user(email="stranger@example.com")
        self.conversation = Conversation.objects.create(
            customer=self.customer, vendor=self.vendor
        )
        self.messages_url = f"/api/v1/conversations/{self.conversation.id}/messages/"

    def test_participant_can_send_message(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.messages_url, {"body": "Is this available?"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Message.objects.filter(conversation=self.conversation).count(), 1
        )

    def test_non_participant_cannot_send_message(self):
        self.client.force_authenticate(self.stranger)
        response = self.client.post(self.messages_url, {"body": "hi"})
        self.assertIn(
            response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
        )

    def test_blank_body_returns_validation_error(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.messages_url, {"body": ""})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_message_list_is_paginated(self):
        for i in range(3):
            Message.objects.create(
                conversation=self.conversation, sender=self.customer, body=f"msg {i}"
            )

        self.client.force_authenticate(self.customer)
        response = self.client.get(self.messages_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data["data"])
        self.assertIn("count", response.data["data"])
        self.assertEqual(response.data["data"]["count"], 3)

    def test_messages_ordered_oldest_first(self):
        first = Message.objects.create(
            conversation=self.conversation, sender=self.customer, body="1"
        )
        second = Message.objects.create(
            conversation=self.conversation, sender=self.customer, body="2"
        )

        self.client.force_authenticate(self.customer)
        response = self.client.get(self.messages_url)
        ids = [item["id"] for item in response.data["data"]["results"]]
        self.assertEqual(ids, [str(first.id), str(second.id)])


class ConversationCompleteViewTests(APITestCase):
    def setUp(self):
        self.vendor = make_vendor()
        self.customer = make_user(email="customer@example.com")
        self.conversation = Conversation.objects.create(
            customer=self.customer, vendor=self.vendor
        )
        self.complete_url = f"/api/v1/conversations/{self.conversation.id}/complete/"

    def test_vendor_can_mark_completed(self):
        self.client.force_authenticate(self.vendor.user)
        response = self.client.post(self.complete_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["data"]["transaction_status"], TransactionStatus.COMPLETED
        )

    def test_customer_cannot_mark_completed(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.complete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_marking_completed_twice_returns_conflict(self):
        self.client.force_authenticate(self.vendor.user)
        self.client.post(self.complete_url)
        response = self.client.post(self.complete_url)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)


class ConversationMarkReadViewTests(APITestCase):
    def setUp(self):
        self.vendor = make_vendor()
        self.customer = make_user(email="customer@example.com")
        self.conversation = Conversation.objects.create(
            customer=self.customer, vendor=self.vendor
        )
        self.vendor_message = Message.objects.create(
            conversation=self.conversation, sender=self.vendor.user, body="Hello"
        )
        self.read_url = f"/api/v1/conversations/{self.conversation.id}/read/"

    def test_customer_can_mark_conversation_read(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.read_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["marked_read"], 1)
        self.vendor_message.refresh_from_db()
        self.assertIsNotNone(self.vendor_message.read_at)

    def test_non_participant_cannot_mark_read(self):
        stranger = make_user(email="stranger@example.com")
        self.client.force_authenticate(stranger)
        response = self.client.post(self.read_url)
        self.assertIn(
            response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
        )
