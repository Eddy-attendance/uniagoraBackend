"""
apps/chat/services/message_service.py

Business logic for Message creation and read-state. Architecture §12:
"Messages are always persisted via the REST/service layer first, then
broadcast" — this is the single call path used by both the REST view
(ConversationViewSet.messages) and the WebSocket consumer
(ChatConsumer.receive_json), so persistence/validation logic is never
duplicated between the two transports (per the task brief's explicit
instruction).
"""

from django.db import transaction
from django.utils import timezone

from apps.chat.models import Message, MessageType
from apps.chat.services.broadcast import broadcast_new_message
from apps.common.exceptions import ApplicationError, PermissionDeniedError


def _is_participant(conversation, user):
    if conversation.customer_id == user.id:
        return True
    return getattr(conversation.vendor, "user_id", None) == user.id


class MessageService:
    @staticmethod
    @transaction.atomic
    def send(*, conversation, sender, body):
        """
        Persist a TEXT message from `sender` into `conversation`, then
        broadcast it to the conversation's WebSocket group only after the
        transaction commits — never before (Architecture §12: sockets are
        never the system of record; a dropped/failed broadcast must never
        be mistaken for a lost message, and a rolled-back transaction
        must never be broadcast).
        """
        if not _is_participant(conversation, sender):
            raise PermissionDeniedError(
                "You are not a participant in this conversation."
            )

        if not body or not str(body).strip():
            raise ApplicationError(
                "Message body is required.",
                errors={"body": ["This field may not be blank."]},
            )

        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            content_type=MessageType.TEXT,
            body=body,
        )

        transaction.on_commit(lambda: broadcast_new_message(message))
        return message

    @staticmethod
    @transaction.atomic
    def mark_conversation_read(*, conversation, reader):
        """
        Marks every unread message in `conversation` not sent by `reader`
        as read. Granularity (per-conversation bulk mark-read, rather
        than a per-message endpoint) is an Engineering Decision — chat
        README Assumption 5; no frozen document specifies the read-state
        API shape, only that `read_at` (DDS §4.11) drives it.
        """
        if not _is_participant(conversation, reader):
            raise PermissionDeniedError(
                "You are not a participant in this conversation."
            )

        updated = (
            Message.objects.alive()
            .filter(conversation=conversation, read_at__isnull=True)
            .exclude(sender=reader)
            .update(read_at=timezone.now())
        )
        return updated
