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
