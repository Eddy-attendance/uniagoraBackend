from unittest.mock import MagicMock

from django.test import TestCase

from apps.chat.models import Conversation, Message
from apps.chat.serializers import (
    ConversationCreateSerializer,
    ConversationSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)
from apps.chat.tests.helpers import make_product, make_store, make_user, make_vendor
from apps.vendors.models import VendorStatus


def _request_for(user):
    request = MagicMock()
    request.user = user
    return request


class ConversationCreateSerializerTests(TestCase):
    def setUp(self):
        self.vendor = make_vendor()
        self.store = make_store(vendor_profile=self.vendor)

    def test_valid_payload_without_product(self):
        serializer = ConversationCreateSerializer(data={"vendor": str(self.vendor.id)})

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_payload_with_matching_product(self):
        product = make_product(store=self.store)

        serializer = ConversationCreateSerializer(
            data={
                "vendor": str(self.vendor.id),
                "product": str(product.id),
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_rejects_product_belonging_to_a_different_vendor(self):
        other_vendor = make_vendor()
        other_store = make_store(vendor_profile=other_vendor)
        foreign_product = make_product(store=other_store)

        serializer = ConversationCreateSerializer(
            data={
                "vendor": str(self.vendor.id),
                "product": str(foreign_product.id),
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("product", serializer.errors)

    def test_accepts_unverified_vendor_for_service_layer_validation(self):
        """
        Vendor verification is a business rule owned by
        ConversationService.initiate(), not serializer validation.

        The serializer only verifies that the VendorProfile exists and is
        alive. The service must subsequently reject a non-verified vendor
        with the appropriate application-level conflict.
        """
        pending_vendor = make_vendor(status=VendorStatus.PENDING)

        serializer = ConversationCreateSerializer(
            data={"vendor": str(pending_vendor.id)}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)


class ConversationSerializerTests(TestCase):
    def setUp(self):
        self.vendor = make_vendor()
        self.customer = make_user(email="customer@example.com")
        self.conversation = Conversation.objects.create(
            customer=self.customer,
            vendor=self.vendor,
        )

    def test_unread_count_defaults_to_zero_without_annotation(self):
        """
        unread_count is now supplied by the annotated Conversation queryset
        in ConversationViewSet. A bare Conversation instance therefore uses
        the serializer's defensive default of zero.
        """
        serializer = ConversationSerializer(
            self.conversation,
            context={"request": _request_for(self.customer)},
        )

        self.assertEqual(serializer.data["unread_count"], 0)

    def test_unread_count_defaults_to_zero_without_request_context(self):
        serializer = ConversationSerializer(
            self.conversation,
            context={},
        )

        self.assertEqual(serializer.data["unread_count"], 0)

    def test_read_only_fields_cannot_be_overridden(self):
        serializer = ConversationSerializer()

        for field_name in serializer.fields:
            self.assertTrue(serializer.fields[field_name].read_only)


class MessageCreateSerializerTests(TestCase):
    def test_rejects_blank_body(self):
        serializer = MessageCreateSerializer(data={"body": ""})

        self.assertFalse(serializer.is_valid())
        self.assertIn("body", serializer.errors)

    def test_accepts_valid_body(self):
        serializer = MessageCreateSerializer(data={"body": "Is this still available?"})

        self.assertTrue(serializer.is_valid())


class MessageSerializerTests(TestCase):
    def setUp(self):
        self.vendor = make_vendor()
        self.customer = make_user(email="customer@example.com")
        self.conversation = Conversation.objects.create(
            customer=self.customer,
            vendor=self.vendor,
        )
        self.message = Message.objects.create(
            conversation=self.conversation,
            sender=self.customer,
            body="Hi",
        )

    def test_is_own_true_for_sender(self):
        serializer = MessageSerializer(
            self.message,
            context={"request": _request_for(self.customer)},
        )

        self.assertTrue(serializer.data["is_own"])

    def test_is_own_false_for_other_participant(self):
        serializer = MessageSerializer(
            self.message,
            context={"request": _request_for(self.vendor.user)},
        )

        self.assertFalse(serializer.data["is_own"])
