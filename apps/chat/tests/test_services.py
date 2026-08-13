"""
apps/chat/tests/test_services.py

Written, not executed this session — see chat README "Testing".
"""

import threading

from django.db import connection
from django.test import TestCase, TransactionTestCase

from apps.chat.models import Conversation, Message, TransactionStatus
from apps.chat.services.conversation_service import ConversationService
from apps.chat.services.message_service import MessageService
from apps.chat.tests.helpers import make_product, make_store, make_user, make_vendor
from apps.common.exceptions import (
    ApplicationError,
    ConflictError,
    PermissionDeniedError,
)
from apps.vendors.models import VendorStatus


class ConversationServiceInitiateTests(TestCase):
    def setUp(self):
        self.vendor = make_vendor()
        self.store = make_store(vendor_profile=self.vendor)
        self.customer = make_user(email="customer@example.com")

    def test_customer_can_initiate_conversation(self):
        conversation, created = ConversationService.initiate(
            customer=self.customer, vendor=self.vendor
        )
        self.assertEqual(conversation.customer, self.customer)
        self.assertEqual(conversation.vendor, self.vendor)
        self.assertIsNone(conversation.product)
        self.assertTrue(created)

    def test_unverified_vendor_is_rejected(self):
        pending_vendor = make_vendor(status=VendorStatus.PENDING)
        with self.assertRaises(ConflictError):
            ConversationService.initiate(customer=self.customer, vendor=pending_vendor)

    def test_suspended_vendor_is_rejected(self):
        suspended_vendor = make_vendor(status=VendorStatus.SUSPENDED)
        with self.assertRaises(ConflictError):
            ConversationService.initiate(
                customer=self.customer, vendor=suspended_vendor
            )

    def test_vendor_cannot_message_their_own_store(self):
        with self.assertRaises(ConflictError):
            ConversationService.initiate(customer=self.vendor.user, vendor=self.vendor)

    def test_product_must_belong_to_the_specified_vendor(self):
        other_vendor = make_vendor()
        other_store = make_store(vendor_profile=other_vendor)
        foreign_product = make_product(store=other_store)
        with self.assertRaises(ApplicationError):
            ConversationService.initiate(
                customer=self.customer, vendor=self.vendor, product=foreign_product
            )

    def test_product_scoped_conversation_created_successfully(self):
        product = make_product(store=self.store)
        conversation, created = ConversationService.initiate(
            customer=self.customer, vendor=self.vendor, product=product
        )
        self.assertEqual(conversation.product, product)
        self.assertTrue(created)

    def test_initiate_is_idempotent_for_product_scoped_conversation(self):
        product = make_product(store=self.store)
        first, first_created = ConversationService.initiate(
            customer=self.customer, vendor=self.vendor, product=product
        )
        second, second_created = ConversationService.initiate(
            customer=self.customer, vendor=self.vendor, product=product
        )
        self.assertEqual(first.pk, second.pk)
        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(
            Conversation.objects.filter(
                customer=self.customer, vendor=self.vendor, product=product
            ).count(),
            1,
        )

    def test_initiate_is_idempotent_for_store_level_conversation(self):
        """
        DDS §13 Assumption 7: at most one store-level (product-less)
        conversation per (customer, vendor) pair — enforced here at the
        service layer since the DB constraint cannot (NULL-distinct).
        """
        first, first_created = ConversationService.initiate(
            customer=self.customer, vendor=self.vendor
        )
        second, second_created = ConversationService.initiate(
            customer=self.customer, vendor=self.vendor
        )
        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(
            Conversation.objects.filter(
                customer=self.customer, vendor=self.vendor, product=None
            ).count(),
            1,
        )


class ConversationServiceMarkCompletedTests(TestCase):
    def setUp(self):
        self.vendor = make_vendor()
        self.customer = make_user(email="customer@example.com")
        self.conversation = Conversation.objects.create(
            customer=self.customer, vendor=self.vendor
        )

    def test_vendor_can_mark_completed(self):
        updated = ConversationService.mark_completed(
            conversation=self.conversation, actor=self.vendor.user
        )
        self.assertEqual(updated.transaction_status, TransactionStatus.COMPLETED)
        self.assertIsNotNone(updated.completed_at)

    def test_customer_cannot_mark_completed(self):
        with self.assertRaises(PermissionDeniedError):
            ConversationService.mark_completed(
                conversation=self.conversation, actor=self.customer
            )

    def test_unrelated_user_cannot_mark_completed(self):
        stranger = make_user(email="stranger@example.com")
        with self.assertRaises(PermissionDeniedError):
            ConversationService.mark_completed(
                conversation=self.conversation, actor=stranger
            )

    def test_marking_completed_twice_raises_conflict(self):
        ConversationService.mark_completed(
            conversation=self.conversation, actor=self.vendor.user
        )
        self.conversation.refresh_from_db()
        with self.assertRaises(ConflictError):
            ConversationService.mark_completed(
                conversation=self.conversation, actor=self.vendor.user
            )


class MessageServiceSendTests(TestCase):
    def setUp(self):
        self.vendor = make_vendor()
        self.customer = make_user(email="customer@example.com")
        self.conversation = Conversation.objects.create(
            customer=self.customer, vendor=self.vendor
        )

    def test_customer_can_send_message(self):
        message = MessageService.send(
            conversation=self.conversation, sender=self.customer, body="Hi!"
        )
        self.assertEqual(message.sender, self.customer)
        self.assertEqual(message.body, "Hi!")
        self.assertEqual(message.content_type, "TEXT")

    def test_vendor_can_send_message(self):
        message = MessageService.send(
            conversation=self.conversation,
            sender=self.vendor.user,
            body="Hello, how can I help?",
        )
        self.assertEqual(message.sender, self.vendor.user)

    def test_non_participant_cannot_send_message(self):
        stranger = make_user(email="stranger@example.com")
        with self.assertRaises(PermissionDeniedError):
            MessageService.send(
                conversation=self.conversation, sender=stranger, body="Hi"
            )

    def test_blank_body_is_rejected(self):
        with self.assertRaises(ApplicationError):
            MessageService.send(
                conversation=self.conversation, sender=self.customer, body="   "
            )

    def test_missing_body_is_rejected(self):
        with self.assertRaises(ApplicationError):
            MessageService.send(
                conversation=self.conversation, sender=self.customer, body=None
            )


class MessageServiceMarkReadTests(TestCase):
    def setUp(self):
        self.vendor = make_vendor()
        self.customer = make_user(email="customer@example.com")
        self.conversation = Conversation.objects.create(
            customer=self.customer, vendor=self.vendor
        )
        self.customer_message = Message.objects.create(
            conversation=self.conversation, sender=self.customer, body="Hi"
        )
        self.vendor_message = Message.objects.create(
            conversation=self.conversation, sender=self.vendor.user, body="Hello"
        )

    def test_reader_marks_only_others_messages_as_read(self):
        MessageService.mark_conversation_read(
            conversation=self.conversation, reader=self.customer
        )
        self.customer_message.refresh_from_db()
        self.vendor_message.refresh_from_db()
        self.assertIsNone(self.customer_message.read_at)
        self.assertIsNotNone(self.vendor_message.read_at)

    def test_non_participant_cannot_mark_read(self):
        stranger = make_user(email="stranger@example.com")
        with self.assertRaises(PermissionDeniedError):
            MessageService.mark_conversation_read(
                conversation=self.conversation, reader=stranger
            )

    def test_mark_read_is_idempotent(self):
        MessageService.mark_conversation_read(
            conversation=self.conversation, reader=self.customer
        )
        updated_count = MessageService.mark_conversation_read(
            conversation=self.conversation, reader=self.customer
        )
        self.assertEqual(updated_count, 0)


class ConversationServiceConcurrencyTests(TransactionTestCase):
    """
    CTO review fix — concurrency safety for `ConversationService.initiate`.

    Requires `TransactionTestCase` (not `TestCase`): `TestCase` wraps
    each test in a single outer transaction shared across threads via
    the same connection, which cannot exercise real `SELECT ... FOR
    UPDATE` row-lock contention between independent connections.
    `TransactionTestCase` gives each thread its own real connection/
    transaction, at the cost of a slower per-test DB flush — the
    standard, documented trade-off for this class of test. Timing-based
    concurrency tests are inherently a little environment-sensitive;
    the CTO should treat an occasional flaky run under heavy CI load as
    a signal to re-check, not necessarily a regression, though a
    consistent failure indicates the lock isn't working.
    """

    def setUp(self):
        self.vendor = make_vendor()
        self.customer = make_user(email="customer@example.com")

    def test_concurrent_initiate_for_store_level_conversation_creates_exactly_one_row(
        self,
    ):
        results = []
        errors = []
        barrier = threading.Barrier(2)

        def worker():
            try:
                # Each thread needs its own DB connection — Django
                # connections are not thread-safe to share.
                connection.close()
                barrier.wait(timeout=5)
                conversation, created = ConversationService.initiate(
                    customer=self.customer, vendor=self.vendor
                )
                results.append((conversation.pk, created))
            except Exception as exc:  # pragma: no cover - surfaced via errors list
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertEqual(errors, [], f"Worker thread(s) raised: {errors}")
        self.assertEqual(len(results), 2)

        pks = {pk for pk, _ in results}
        created_flags = sorted(created for _, created in results)

        self.assertEqual(
            len(pks), 1, "Both requests must resolve to the same Conversation row."
        )
        self.assertEqual(
            created_flags,
            [False, True],
            "Exactly one request should have created the row; the other resolves to it.",
        )
        self.assertEqual(
            Conversation.objects.filter(
                customer=self.customer, vendor=self.vendor, product=None
            ).count(),
            1,
        )
