import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from apps.common.exceptions import ApplicationError

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    Route: `ws/chat/<uuid:conversation_id>/` (see routing.py).
    Group: `conversation_{conversation_id}` — a user is only ever added
    to the group for a conversation they are already authorized to view;
    there is no mechanism to join any other group.
    """

    async def connect(self):
        user = self.scope.get("user")
        if user is None or isinstance(user, AnonymousUser) or not user.is_authenticated:
            # Close before accept() — the client observes a refused
            # connection, not an accepted-then-dropped one.
            await self.close(code=4401)
            return

        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        conversation = await self._get_authorized_conversation(user)
        if conversation is None:
            await self.close(code=4403)
            return

        self.user = user
        self.group_name = f"conversation_{self.conversation_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        body = content.get("body")
        try:
            await self._create_message(body)
        except ApplicationError as exc:
            # Expected, client-safe: same message shape the REST
            # endpoint's exception handler would return for this same
            # failure (e.g. "You are not a participant in this
            # conversation.", "Message body is required."). Never
            # includes exception internals.
            await self.send_json({"error": exc.message})
        except Exception:
            # Unexpected — a real bug, not a business-rule rejection.
            # Log server-side with full detail; the client only ever
            # sees a generic, non-leaking message.
            logger.exception(
                "Unexpected error while creating chat message (conversation_id=%s)",
                self.conversation_id,
            )
            await self.send_json({"error": "Unable to send message."})

    async def chat_message(self, event):
        """Channel-layer group_send handler — `type: "chat.message"`."""
        await self.send_json(event["message"])

    @database_sync_to_async
    def _get_authorized_conversation(self, user):
        from apps.chat.models import Conversation

        try:
            conversation = (
                Conversation.objects.alive()
                .select_related("vendor")
                .get(id=self.conversation_id)
            )
        except Conversation.DoesNotExist:
            return None
        if (
            conversation.customer_id == user.id
            or conversation.vendor.user_id == user.id
        ):
            return conversation
        return None

    @database_sync_to_async
    def _create_message(self, body):
        from apps.chat.models import Conversation
        from apps.chat.services.message_service import MessageService

        conversation = (
            Conversation.objects.alive()
            .select_related("vendor")
            .get(id=self.conversation_id)
        )
        MessageService.send(conversation=conversation, sender=self.user, body=body)
