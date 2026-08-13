"""
apps/chat/views.py

Thin views only — every mutating action delegates immediately to a
service (Architecture §7).

Response envelope (CTO review fix): views now call `common.response
.success_response()` explicitly on every success path, matching the
current project convention (`products` and other recent apps construct
the envelope explicitly rather than relying solely on the renderer).
The global `EnvelopeJSONRenderer` remains in place as the defensive
backstop it was always meant to be (ADR-006) — it is not removed or
altered, and failure paths still rely entirely on it plus
`custom_exception_handler`: no view here calls `error_response()`
directly, since every expected failure is already raised as an
`ApplicationError` subclass by a service or a DRF `ValidationError` by a
serializer, and `common` EDD §26 pitfall #5 explicitly warns against
reintroducing per-view try/except for exactly that case. As with
`EDD_users_authentication.md` §10 item 6, `success_response()`'s exact
keyword arguments (`data=`, `message=`, `status=`) are reused from that
already-established, not-yet-source-verified inference.
"""

from django.db.models import Count, Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action

from apps.chat.models import Conversation
from apps.chat.permissions import IsConversationParticipant
from apps.chat.serializers import (
    ConversationCreateSerializer,
    ConversationSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)
from apps.chat.services.conversation_service import ConversationService
from apps.chat.services.message_service import MessageService
from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.core.permissions import IsAuthenticatedCustomer


class ConversationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    /api/v1/conversations/

    Route shape — including the single, unified "my conversations" list
    covering both the customer side and the vendor side of every thread
    a user participates in, and messages/read/complete as sub-actions on
    the conversation resource rather than a separate top-level messages
    endpoint — is an Engineering Implementation Decision. No frozen
    document names an exact chat route list; only the underlying DDS §11
    query patterns and PRD §10/§7 workflows are specified. See the chat
    README, "API Layer", for the full reasoning.
    """

    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticatedCustomer]
    pagination_class = StandardResultsSetPagination
    lookup_field = "id"

    def get_queryset(self):
        """
        CTO review fix: `unread_count` is annotated here via a single
        conditional `Count` per query — not computed per-row in the
        serializer (previously an N+1: one query per conversation in a
        list of N). The filter mirrors exactly what the old per-object
        query did (`read_at IS NULL`, excluding the requesting user's
        own messages, alive rows only), so the value is identical — just
        computed once, in SQL, for the whole page. Works unchanged for
        both a customer's and a vendor's own conversations, since `user`
        is always `request.user` regardless of which side of the thread
        they're on. The existing partial index on `Message.read_at`
        (`WHERE read_at IS NULL`) remains useful to the planner for the
        `read_at IS NULL` predicate inside this annotation.
        """
        user = self.request.user
        unread_count = Count(
            "messages",
            filter=(
                Q(messages__read_at__isnull=True)
                & Q(messages__is_deleted=False)
                & ~Q(messages__sender=user)
            ),
            distinct=True,
        )
        return (
            Conversation.objects.alive()
            .select_related("vendor", "vendor__user", "customer", "product")
            .filter(Q(customer=user) | Q(vendor__user=user))
            .annotate(unread_count=unread_count)
            .order_by("-updated_at")
        )

    def get_permissions(self):
        if self.action in ("retrieve", "complete", "messages", "mark_read"):
            return [IsAuthenticatedCustomer(), IsConversationParticipant()]
        return [IsAuthenticatedCustomer()]

    def _serialize_annotated(self, conversation):
        """
        Re-fetches `conversation` through the annotated queryset before
        serializing, so `create`/`complete` responses carry a correct,
        SQL-computed `unread_count` too (not just list/retrieve) — one
        cheap single-row PK lookup, not a per-list-item cost, so this
        does not reintroduce the N+1 this fix removes.
        """
        annotated = self.get_queryset().get(pk=conversation.pk)
        return self.get_serializer(annotated)

    def create(self, request, *args, **kwargs):
        """
        CTO review fix: `ConversationService.initiate` now returns
        `(conversation, created)`. A brand-new conversation returns 201;
        an idempotent resolution to an already-existing conversation
        returns 200 — the previous implementation returned 201
        unconditionally, which was semantically incorrect for the
        already-exists case.
        """
        serializer = ConversationCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        conversation, created = ConversationService.initiate(
            customer=request.user,
            vendor=serializer.validated_data["vendor"],
            product=serializer.validated_data.get("product"),
        )
        output = self._serialize_annotated(conversation)
        return success_response(
            data=output.data,
            message="Conversation created."
            if created
            else "Conversation already exists.",
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, *args, **kwargs):
        conversation = self.get_object()
        conversation = ConversationService.mark_completed(
            conversation=conversation, actor=request.user
        )
        output = self._serialize_annotated(conversation)
        return success_response(
            data=output.data,
            message="Transaction marked as completed.",
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages(self, request, *args, **kwargs):
        conversation = self.get_object()

        if request.method == "POST":
            serializer = MessageCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            message = MessageService.send(
                conversation=conversation,
                sender=request.user,
                body=serializer.validated_data["body"],
            )
            output = MessageSerializer(message, context={"request": request})
            return success_response(
                data=output.data,
                message="Message sent.",
                status=status.HTTP_201_CREATED,
            )

        queryset = conversation.messages.alive().select_related("sender")
        page = self.paginate_queryset(queryset)
        serializer = MessageSerializer(page, many=True, context={"request": request})
        # StandardResultsSetPagination.get_paginated_response() already
        # builds the envelope via success_response() internally (common
        # EDD §10) — wrapping it again here would double-envelope the
        # payload.
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, *args, **kwargs):
        """
        Returns 200 (not the previous 204) now that the response carries
        an explicit envelope body — a 204 must not have a body per HTTP
        semantics, which would conflict with unconditionally calling
        `success_response()` here. `marked_read` reports how many
        messages actually transitioned, which 204's empty body could
        not.
        """
        conversation = self.get_object()
        updated = MessageService.mark_conversation_read(
            conversation=conversation, reader=request.user
        )
        return success_response(
            data={"marked_read": updated},
            message="Conversation marked as read.",
            status=status.HTTP_200_OK,
        )
