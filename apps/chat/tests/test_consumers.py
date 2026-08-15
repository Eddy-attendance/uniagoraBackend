from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.chat.middleware import JWTAuthMiddlewareStack
from apps.chat.models import Conversation
from apps.chat.routing import websocket_urlpatterns
from apps.chat.tests.helpers import make_user, make_vendor


@database_sync_to_async
def _access_token_for(user):
    return str(RefreshToken.for_user(user).access_token)


def _make_application():
    return JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns))


class ChatConsumerConnectionTests(TransactionTestCase):
    def setUp(self):
        self.vendor = make_vendor()
        self.customer = make_user(email="customer@example.com")
        self.stranger = make_user(email="stranger@example.com")
        self.conversation = Conversation.objects.create(
            customer=self.customer, vendor=self.vendor
        )
        self.path = f"/ws/chat/{self.conversation.id}/"

    async def test_unauthenticated_connection_is_rejected(self):
        communicator = WebsocketCommunicator(_make_application(), self.path)
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_non_participant_connection_is_rejected(self):
        token = await _access_token_for(self.stranger)
        communicator = WebsocketCommunicator(
            _make_application(), f"{self.path}?token={token}"
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_customer_can_connect(self):
        token = await _access_token_for(self.customer)
        communicator = WebsocketCommunicator(
            _make_application(), f"{self.path}?token={token}"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_vendor_user_can_connect(self):
        token = await _access_token_for(self.vendor.user)
        communicator = WebsocketCommunicator(
            _make_application(), f"{self.path}?token={token}"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()


class ChatConsumerMessageFlowTests(TransactionTestCase):
    def setUp(self):
        self.vendor = make_vendor()
        self.customer = make_user(email="customer@example.com")
        self.conversation = Conversation.objects.create(
            customer=self.customer, vendor=self.vendor
        )
        self.path = f"/ws/chat/{self.conversation.id}/"

    async def test_sent_message_is_persisted_and_broadcast_to_group(self):
        token = await _access_token_for(self.customer)
        communicator = WebsocketCommunicator(
            _make_application(), f"{self.path}?token={token}"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_json_to({"body": "Is this still available?"})
        response = await communicator.receive_json_from()

        self.assertEqual(response["body"], "Is this still available?")
        exists = await self._message_exists()
        self.assertTrue(exists)

        await communicator.disconnect()

    async def test_blank_body_returns_error_without_persisting(self):
        """
        Also documents the CTO review fix directly: the consumer no
        longer pre-checks blank body itself — this now flows through
        `MessageService.send`'s own validation (raises `ApplicationError`,
        caught in `receive_json`), so the same rule is enforced exactly
        once, not duplicated between transports.
        """
        token = await _access_token_for(self.customer)
        communicator = WebsocketCommunicator(
            _make_application(), f"{self.path}?token={token}"
        )
        await communicator.connect()

        await communicator.send_json_to({"body": "   "})
        response = await communicator.receive_json_from()

        self.assertIn("error", response)
        exists = await self._message_exists()
        self.assertFalse(exists)
        await communicator.disconnect()

    async def test_unexpected_exception_returns_generic_message_not_internals(self):
        """
        CTO review fix: an unexpected (non-`ApplicationError`) exception
        must never leak `str(exc)` to the client — only a generic,
        client-safe message. Forces the failure by pointing the service
        call at a conversation id that will raise `Conversation
        .DoesNotExist` deep inside `_create_message` (simulating any
        unexpected failure, not just this specific one).
        """
        token = await _access_token_for(self.customer)
        communicator = WebsocketCommunicator(
            _make_application(), f"{self.path}?token={token}"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Simulate an unexpected failure inside message creation without
        # relying on any particular internal exception type — deleting
        # the conversation out from under an already-connected socket is
        # a legitimate (if rare) way to force `_create_message`'s lookup
        # to fail unexpectedly.
        await self._hard_delete_conversation()

        await communicator.send_json_to({"body": "Hello?"})
        response = await communicator.receive_json_from()

        self.assertEqual(response, {"error": "Unable to send message."})
        await communicator.disconnect()

    async def _hard_delete_conversation(self):
        from channels.db import database_sync_to_async

        await database_sync_to_async(self.conversation.delete)(hard=True)

    async def _message_exists(self):
        from channels.db import database_sync_to_async

        from apps.chat.models import Message

        return await database_sync_to_async(
            Message.objects.filter(conversation=self.conversation).exists
        )()
