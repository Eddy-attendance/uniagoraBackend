from django.conf import settings
from django.db import models

from apps.common.fields import CloudinaryImageField
from apps.common.models import BaseModel


class TransactionStatus(models.TextChoices):
    """Conversation.transaction_status"""

    ONGOING = "ONGOING", "Ongoing"
    COMPLETED = "COMPLETED", "Completed"


class MessageType(models.TextChoices):
    """Message.content_type Only TEXT is ever created in MVP."""

    TEXT = "TEXT", "Text"
    IMAGE = "IMAGE", "Image"  # schema-ready, unused in MVP


class AttachmentType(models.TextChoices):
    """MessageAttachment.attachment_type"""

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
    body = models.TextField(  # noqa: DJ001
        null=True, blank=True
    )
    read_at = models.DateTimeField(  # noqa: DJ001
        null=True, blank=True
    )

    class Meta:
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
        return (self.body or "")[:50]

    @property
    def is_read(self):
        return self.read_at is not None


class MessageAttachment(BaseModel):
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
