"""
apps/chat/tests/test_models.py

Written, not executed (no live Django/PostgreSQL environment this
session) — see the chat README, "Testing", for the standing disclosure
format used across every prior EDD.
"""

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.chat.models import Conversation, Message, MessageAttachment, TransactionStatus
from apps.chat.tests.helpers import make_product, make_store, make_user, make_vendor


class ConversationModelTests(TestCase):
    def setUp(self):
        self.vendor = make_vendor()
        self.customer = make_user(email="customer@example.com")

    def test_str_representation(self):
        conversation = Conversation.objects.create(
            customer=self.customer, vendor=self.vendor
        )
        self.assertEqual(
            str(conversation), f"{self.customer} \u2194 {self.vendor.store_name}"
        )

    def test_default_transaction_status_is_ongoing(self):
        conversation = Conversation.objects.create(
            customer=self.customer, vendor=self.vendor
        )
        self.assertEqual(conversation.transaction_status, TransactionStatus.ONGOING)
        self.assertFalse(conversation.is_completed)
        self.assertIsNone(conversation.completed_at)

    def test_is_completed_property(self):
        conversation = Conversation.objects.create(
            customer=self.customer,
            vendor=self.vendor,
            transaction_status=TransactionStatus.COMPLETED,
        )
        self.assertTrue(conversation.is_completed)

    def test_product_is_optional(self):
        conversation = Conversation.objects.create(
            customer=self.customer, vendor=self.vendor
        )
        self.assertIsNone(conversation.product)

    def test_product_scoped_conversation(self):
        store = make_store(vendor_profile=self.vendor)
        product = make_product(store=store)
        conversation = Conversation.objects.create(
            customer=self.customer, vendor=self.vendor, product=product
        )
        self.assertEqual(conversation.product, product)

    def test_unique_constraint_blocks_duplicate_product_scoped_conversation(self):
        store = make_store(vendor_profile=self.vendor)
        product = make_product(store=store)
        Conversation.objects.create(
            customer=self.customer, vendor=self.vendor, product=product
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Conversation.objects.create(
                    customer=self.customer, vendor=self.vendor, product=product
                )

    def test_null_product_conversations_are_not_blocked_by_the_db_constraint(self):
        """
        Documents DDS §13 Assumption 7's PostgreSQL NULL-distinct
        behavior directly: the DB-level UNIQUE(customer, vendor, product)
        constraint does NOT prevent two product-less rows for the same
        pair — this is exactly why ConversationService.initiate() must
        enforce "at most one" at the service layer instead.
        """
        Conversation.objects.create(
            customer=self.customer, vendor=self.vendor, product=None
        )
        second = Conversation.objects.create(
            customer=self.customer, vendor=self.vendor, product=None
        )
        self.assertIsNotNone(second.pk)
        self.assertEqual(
            Conversation.objects.filter(
                customer=self.customer, vendor=self.vendor, product=None
            ).count(),
            2,
        )

    def test_default_ordering_is_updated_at_descending(self):
        older = Conversation.objects.create(customer=self.customer, vendor=self.vendor)
        newer_vendor = make_vendor()
        newer = Conversation.objects.create(customer=self.customer, vendor=newer_vendor)
        self.assertEqual(list(Conversation.objects.alive()), [newer, older])

    def test_soft_delete_regression(self):
        conversation = Conversation.objects.create(
            customer=self.customer, vendor=self.vendor
        )
        conversation.delete()
        self.assertTrue(Conversation.objects.get(pk=conversation.pk).is_deleted)
        self.assertIn(conversation, Conversation.objects.all())
        self.assertNotIn(conversation, Conversation.objects.alive())


class MessageModelTests(TestCase):
    def setUp(self):
        self.vendor = make_vendor()
        self.customer = make_user(email="customer@example.com")
        self.conversation = Conversation.objects.create(
            customer=self.customer, vendor=self.vendor
        )

    def test_str_truncates_body_to_50_chars(self):
        long_body = "x" * 80
        message = Message.objects.create(
            conversation=self.conversation, sender=self.customer, body=long_body
        )
        self.assertEqual(len(str(message)), 50)

    def test_is_read_property(self):
        message = Message.objects.create(
            conversation=self.conversation, sender=self.customer, body="hi"
        )
        self.assertFalse(message.is_read)
        message.read_at = message.created_at
        self.assertTrue(message.is_read)

    def test_default_content_type_is_text(self):
        message = Message.objects.create(
            conversation=self.conversation, sender=self.customer, body="hi"
        )
        self.assertEqual(message.content_type, "TEXT")

    def test_default_ordering_is_created_at_ascending(self):
        first = Message.objects.create(
            conversation=self.conversation, sender=self.customer, body="1"
        )
        second = Message.objects.create(
            conversation=self.conversation, sender=self.customer, body="2"
        )
        self.assertEqual(list(self.conversation.messages.alive()), [first, second])

    def test_cascade_delete_from_conversation_hard_delete(self):
        message = Message.objects.create(
            conversation=self.conversation, sender=self.customer, body="hi"
        )
        self.conversation.delete(hard=True)
        self.assertFalse(Message.objects.filter(pk=message.pk).exists())


class MessageAttachmentModelTests(TestCase):
    def setUp(self):
        vendor = make_vendor()
        customer = make_user(email="customer2@example.com")
        conversation = Conversation.objects.create(customer=customer, vendor=vendor)
        self.message = Message.objects.create(
            conversation=conversation, sender=customer, body="hi"
        )

    def test_one_to_one_with_message(self):
        attachment = MessageAttachment.objects.create(
            message=self.message, file="chat/img1.jpg"
        )
        self.assertEqual(self.message.attachment, attachment)

    def test_cascade_delete_from_message_hard_delete(self):
        attachment = MessageAttachment.objects.create(
            message=self.message, file="chat/img1.jpg"
        )
        self.message.delete(hard=True)
        self.assertFalse(MessageAttachment.objects.filter(pk=attachment.pk).exists())
