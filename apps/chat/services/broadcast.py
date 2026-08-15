from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def _serialize_message(message):
    return {
        "id": str(message.id),
        "conversation_id": str(message.conversation_id),
        "sender_id": str(message.sender_id),
        "content_type": message.content_type,
        "body": message.body,
        "read_at": message.read_at.isoformat() if message.read_at else None,
        "created_at": message.created_at.isoformat(),
    }


def broadcast_new_message(message):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        f"conversation_{message.conversation_id}",
        {
            "type": "chat.message",
            "message": _serialize_message(message),
        },
    )
