from django.contrib import admin

from apps.chat.models import Conversation, Message, MessageAttachment
from apps.common.admin import SoftDeleteAdminMixin


@admin.register(Conversation)
class ConversationAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "vendor",
        "product",
        "transaction_status",
        "created_at",
    )
    list_filter = ("transaction_status",)
    search_fields = ("customer__email", "vendor__store_name")
    raw_id_fields = ("customer", "vendor", "product")


@admin.register(Message)
class MessageAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "conversation",
        "sender",
        "content_type",
        "read_at",
        "created_at",
    )
    list_filter = ("content_type",)
    raw_id_fields = ("conversation", "sender")


@admin.register(MessageAttachment)
class MessageAttachmentAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("id", "message", "attachment_type")
    raw_id_fields = ("message",)
