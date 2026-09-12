from django.db.models import Count, Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, serializers, status, viewsets
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
from apps.common.openapi import (
    paginated_response_schema,
    success_response_schema,
)
from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.core.permissions import IsAuthenticatedCustomer


class MarkConversationReadDataSerializer(serializers.Serializer):
    marked_read = serializers.IntegerField()


class ConversationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticatedCustomer]
    pagination_class = StandardResultsSetPagination
    lookup_field = "id"

    def get_queryset(self):
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
            .select_related(
                "vendor",
                "vendor__user",
                "customer",
                "product",
            )
            .filter(Q(customer=user) | Q(vendor__user=user))
            .annotate(unread_count=unread_count)
            .order_by("-updated_at")
        )

    def get_permissions(self):
        if self.action in (
            "retrieve",
            "complete",
            "messages",
            "mark_read",
        ):
            return [
                IsAuthenticatedCustomer(),
                IsConversationParticipant(),
            ]

        return [IsAuthenticatedCustomer()]

    @extend_schema(
        summary="List the authenticated user's conversations.",
        request=None,
        responses={
            status.HTTP_200_OK: paginated_response_schema(
                "ConversationListResponse",
                ConversationSerializer,
            ),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def _serialize_annotated(self, conversation):
        annotated = self.get_queryset().get(pk=conversation.pk)
        return self.get_serializer(annotated)

    @extend_schema(
        summary="Initiate a conversation with a vendor (customers only).",
        request=ConversationCreateSerializer,
        responses={
            status.HTTP_200_OK: success_response_schema(
                "ConversationExistingResponse",
                ConversationSerializer,
            ),
            status.HTTP_201_CREATED: success_response_schema(
                "ConversationCreateResponse",
                ConversationSerializer,
            ),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = ConversationCreateSerializer(
            data=request.data,
            context={"request": request},
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
            message=(
                "Conversation created." if created else "Conversation already exists."
            ),
            status=(status.HTTP_201_CREATED if created else status.HTTP_200_OK),
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Conversation UUID.",
            )
        ],
        request=None,
        responses={
            status.HTTP_200_OK: success_response_schema(
                "ConversationRetrieveResponse",
                ConversationSerializer,
            ),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Conversation UUID.",
            )
        ],
        request=None,
        responses={
            status.HTTP_200_OK: success_response_schema(
                "ConversationCompleteResponse",
                ConversationSerializer,
            ),
        },
    )
    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, *args, **kwargs):
        conversation = self.get_object()

        conversation = ConversationService.mark_completed(
            conversation=conversation,
            actor=request.user,
        )

        output = self._serialize_annotated(conversation)

        return success_response(
            data=output.data,
            message="Transaction marked as completed.",
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        methods=["get"],
        parameters=[
            OpenApiParameter(
                name="id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Conversation UUID.",
            )
        ],
        request=None,
        responses={
            status.HTTP_200_OK: paginated_response_schema(
                "ConversationMessageListResponse",
                MessageSerializer,
            ),
        },
    )
    @extend_schema(
        methods=["post"],
        parameters=[
            OpenApiParameter(
                name="id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Conversation UUID.",
            )
        ],
        request=MessageCreateSerializer,
        responses={
            status.HTTP_201_CREATED: success_response_schema(
                "ConversationMessageCreateResponse",
                MessageSerializer,
            ),
        },
    )
    @action(
        detail=True,
        methods=["get", "post"],
        url_path="messages",
    )
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

            output = MessageSerializer(
                message,
                context={"request": request},
            )

            return success_response(
                data=output.data,
                message="Message sent.",
                status=status.HTTP_201_CREATED,
            )

        queryset = conversation.messages.alive().select_related("sender")

        page = self.paginate_queryset(queryset)

        serializer = MessageSerializer(
            page,
            many=True,
            context={"request": request},
        )

        return self.get_paginated_response(serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="id",
                type=str,
                location=OpenApiParameter.PATH,
                description="Conversation UUID.",
            )
        ],
        request=None,
        responses={
            status.HTTP_200_OK: success_response_schema(
                "ConversationMarkReadResponse",
                MarkConversationReadDataSerializer,
            ),
        },
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="read",
    )
    def mark_read(self, request, *args, **kwargs):
        conversation = self.get_object()

        updated = MessageService.mark_conversation_read(
            conversation=conversation,
            reader=request.user,
        )

        return success_response(
            data={"marked_read": updated},
            message="Conversation marked as read.",
            status=status.HTTP_200_OK,
        )
