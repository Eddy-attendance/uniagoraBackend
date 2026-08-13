"""
apps/chat/models.py

Chat domain models: Conversation, Message, MessageAttachment.
Reproduces DDS §4.10-4.12 field-for-field. All models inherit
apps.common.models.BaseModel (UUID PK, created_at, updated_at, is_deleted,
soft delete via .delete()/.restore(), unfiltered-by-default `.objects`
with `.alive()`/`.dead()` supplied by common.managers.SoftDeleteManager).

"""

from django.conf import settings
from django.db import models

from apps.common.fields import CloudinaryImageField
from apps.common.models import BaseModel


class TransactionStatus(models.TextChoices):
    """Conversation.transaction_status — DDS §5."""

    ONGOING = "ONGOING", "Ongoing"
    COMPLETED = "COMPLETED", "Completed"


class MessageType(models.TextChoices):
    """Message.content_type — DDS §5. Only TEXT is ever created in MVP."""

    TEXT = "TEXT", "Text"
    IMAGE = "IMAGE", "Image"  # schema-ready, unused in MVP


class AttachmentType(models.TextChoices):
    """MessageAttachment.attachment_type — DDS §5."""

    IMAGE = "IMAGE", "Image"


class Conversation(BaseModel):
    """
    A Customer-initiated thread with a Vendor, optionally scoped to a
    Product. Also the sole anchor for review eligibility via
    `transaction_status`.
    """

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="conversations_as_customer",
    )
    vendor = models.ForeignKey(
        "vendors.VendorProfile",
        on_delete=models.PROTECT,
        related_name="conversations",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        related_name="conversations",
        null=True,
        blank=True,
    )
    transaction_status = models.CharField(
        max_length=15,
        choices=TransactionStatus.choices,
        default=TransactionStatus.ONGOING,
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # Engineering Decision: overrides BaseModel's inherited
        # "-created_at" default so unordered querysets match the DDS §11
        # "My conversations" / "Vendor inbox" read patterns, both
        # expressed as `.order_by('-updated_at')` — mirrors ADR-U2's
        # precedent (universities app) of aligning default ordering with
        # the documented primary read pattern for a model.
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["customer"], name="chat_conv_customer_idx"),
            models.Index(fields=["vendor"], name="chat_conv_vendor_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "vendor", "product"],
                name="unique_customer_vendor_product_conversation",
            ),
        ]

    def __str__(self):
        return f"{self.customer} \u2194 {self.vendor.store_name}"

    @property
    def is_completed(self):
        return self.transaction_status == TransactionStatus.COMPLETED


class Message(BaseModel):
    """An individual message within a Conversation."""

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_messages",
    )
    content_type = models.CharField(
        max_length=10,
        choices=MessageType.choices,
        default=MessageType.TEXT,
    )
    # Required when content_type=TEXT; blank permitted only when an
    # attachment carries the content instead — enforced at the
    # serializer/service layer per DDS §4.11/§7.2, not as a DB constraint.
    body = models.TextField(  # noqa: DJ001
        null=True, blank=True
    )
    read_at = models.DateTimeField(  # noqa: DJ001
        null=True, blank=True
    )

    class Meta:
        # Overrides BaseModel's "-created_at" default: a chat thread reads
        # oldest-first (DDS §11: "Chat history (ordered thread)").
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["conversation", "created_at"], name="chat_message_thread_idx"
            ),
            models.Index(
                fields=["read_at"],
                name="chat_message_unread_idx",
                condition=models.Q(read_at__isnull=True),
            ),
        ]

    def __str__(self):
        # Single confirmed consumer for text truncation (DDS §4.11) —
        # inlined directly here per common EDD ADR-004's own precedent
        # (truncate_text() was removed from `common` for exactly this
        # reason: one consumer does not clear the shared-abstraction bar).
        return (self.body or "")[:50]

    @property
    def is_read(self):
        return self.read_at is not None


class MessageAttachment(BaseModel):
    """
    Schema-ready, unused-in-MVP support for image attachments (DDS §4.12).
    No serializer, view, or URL exposes this model in this delivery — see
    the chat README "Scope" section for the explicit MVP boundary.
    """

    message = models.OneToOneField(
        Message,
        on_delete=models.CASCADE,
        related_name="attachment",
    )
    file = CloudinaryImageField(folder="chat_attachments")
    attachment_type = models.CharField(
        max_length=10,
        choices=AttachmentType.choices,
        default=AttachmentType.IMAGE,
    )

    def __str__(self):
        return f"Attachment for message {self.message_id}"
