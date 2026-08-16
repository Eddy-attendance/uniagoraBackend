from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView

from apps.chat.models import Conversation
from apps.chat.permissions import IsConversationParticipant
from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.core.permissions import IsAuthenticatedCustomer
from apps.stores.models import Store

from .models import Review
from .permissions import IsReviewOwner
from .serializers import (
    ReviewCreateSerializer,
    ReviewSerializer,
    ReviewUpdateSerializer,
)
from .services import _UNSET, ReviewService


class ConversationReviewView(APIView):
    """
    GET  /api/v1/reviews/conversations/{conversation_id}/
         Participant-only review retrieval.

    POST /api/v1/reviews/conversations/{conversation_id}/
         Customer review creation.
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [
                IsAuthenticatedCustomer(),
                IsConversationParticipant(),
            ]

        return [IsAuthenticatedCustomer()]

    @extend_schema(
        request=None,
        responses={status.HTTP_200_OK: ReviewSerializer},
    )
    def get(self, request, conversation_id):
        conversation = get_object_or_404(
            Conversation.objects.alive(),
            pk=conversation_id,
        )
        self.check_object_permissions(request, conversation)

        review = ReviewService.get_for_conversation(
            conversation=conversation,
        )
        serializer = ReviewSerializer(review)

        return success_response(data=serializer.data)

    @extend_schema(
        request=ReviewCreateSerializer,
        responses={status.HTTP_201_CREATED: ReviewSerializer},
    )
    def post(self, request, conversation_id):
        conversation = get_object_or_404(
            Conversation.objects.alive(),
            pk=conversation_id,
        )

        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        review = ReviewService.create(
            conversation=conversation,
            customer=request.user,
            rating=serializer.validated_data["rating"],
            comment=serializer.validated_data.get("comment"),
        )

        output_serializer = ReviewSerializer(review)

        return success_response(
            data=output_serializer.data,
            message="Review created.",
            status=status.HTTP_201_CREATED,
        )


class ReviewDetailView(APIView):
    """
    GET   /api/v1/reviews/{id}/
          Retrieve a review.

    PATCH /api/v1/reviews/{id}/
          Update a review. Only the review owner may edit it.
    """

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [
                IsAuthenticatedCustomer(),
                IsReviewOwner(),
            ]

        return [IsAuthenticatedCustomer()]

    def get_object(self, pk):
        review = get_object_or_404(
            Review.objects.alive().select_related(
                "conversation__customer",
                "store",
            ),
            pk=pk,
        )

        self.check_object_permissions(self.request, review)

        return review

    @extend_schema(
        request=None,
        responses={status.HTTP_200_OK: ReviewSerializer},
    )
    def get(self, request, pk):
        review = self.get_object(pk)
        serializer = ReviewSerializer(review)

        return success_response(data=serializer.data)

    @extend_schema(
        request=ReviewUpdateSerializer,
        responses={status.HTTP_200_OK: ReviewSerializer},
    )
    def patch(self, request, pk):
        review = self.get_object(pk)

        serializer = ReviewUpdateSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        updated_review = ReviewService.update(
            review=review,
            actor=request.user,
            rating=serializer.validated_data.get(
                "rating",
                _UNSET,
            ),
            comment=serializer.validated_data.get(
                "comment",
                _UNSET,
            ),
        )

        output_serializer = ReviewSerializer(updated_review)

        return success_response(
            data=output_serializer.data,
            message="Review updated.",
        )


class StoreReviewListView(ListAPIView):
    """
    GET /api/v1/reviews/stores/{store_slug}/
    Returns paginated reviews for an active store, newest first.
    """

    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedCustomer]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        store = get_object_or_404(
            Store.objects.alive().filter(is_active=True),
            slug=self.kwargs["store_slug"],
        )

        return (
            Review.objects.alive()
            .filter(store=store)
            .select_related(
                "conversation__customer",
                "store",
            )
            .order_by("-created_at")
        )
