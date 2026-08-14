"""Thin views — all business logic delegated to services.py, per
Architecture §7. Every view explicitly calls `common.response
.success_response()` on its success path (the current project convention,
established by `chat` EDD §7a fix #4), rather than relying solely on
`EnvelopeJSONRenderer` as a backstop.

Ownership is enforced two ways, matching the `users`/`stores` "me"-route
precedent: (1) every queryset is scoped to `request.user` at the view
layer, so a non-owned object simply doesn't exist from the requester's
point of view (a 404, via DRF's own `get_object_or_404`) — no client-
supplied identifier is ever trusted; (2) the service layer re-verifies
ownership as defense-in-depth (see services.py). No new `core`-level
permission class was needed for object-level ownership here, unlike
`chat.IsConversationParticipant` — a Conversation has *two* legitimate
sides (customer and vendor); a Notification/DeviceToken has exactly one
(the recipient/user), which plain queryset scoping already expresses
correctly.
"""

from rest_framework import generics, status
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView

from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.core.permissions import IsAuthenticatedCustomer

from .models import DeviceToken, Notification
from .serializers import (
    DeviceTokenRegisterSerializer,
    DeviceTokenSerializer,
    NotificationSerializer,
)
from .services import DeviceTokenService, NotificationService


class NotificationListView(generics.ListAPIView):
    """GET /api/v1/notifications/ — own notifications, paginated.

    `?unread=true` narrows to unread-only (DDS §11's "Unread notifications
    badge" pattern, applied to listing rather than just counting).
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticatedCustomer]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        unread_param = self.request.query_params.get("unread")
        unread_only = unread_param is not None and unread_param.lower() == "true"
        return NotificationService.get_for_user(
            self.request.user, unread_only=unread_only
        )


class NotificationUnreadCountView(APIView):
    """GET /api/v1/notifications/unread-count/"""

    permission_classes = [IsAuthenticatedCustomer]

    def get(self, request):
        count = NotificationService.unread_count(request.user)
        return success_response(data={"unread_count": count})


class NotificationMarkReadView(APIView):
    """POST /api/v1/notifications/{id}/read/"""

    permission_classes = [IsAuthenticatedCustomer]

    def post(self, request, pk):
        notification = get_object_or_404(
            Notification.objects.alive().filter(recipient=request.user), pk=pk
        )
        notification = NotificationService.mark_read(
            notification=notification, user=request.user
        )
        serializer = NotificationSerializer(notification)
        return success_response(
            data=serializer.data, message="Notification marked as read."
        )


class NotificationMarkAllReadView(APIView):
    """POST /api/v1/notifications/read-all/"""

    permission_classes = [IsAuthenticatedCustomer]

    def post(self, request):
        marked = NotificationService.mark_all_read(request.user)
        return success_response(
            data={"marked_read": marked}, message="Notifications marked as read."
        )


class DeviceTokenListCreateView(APIView):
    """GET/POST /api/v1/notifications/device-tokens/

    Not paginated — a user's device-token count is small and bounded by
    real-world device ownership, not marketplace data volume; pagination
    here would be premature abstraction (project's stated avoid-over-
    engineering principle).
    """

    permission_classes = [IsAuthenticatedCustomer]

    def get(self, request):
        tokens = DeviceTokenService.get_for_user(request.user, active_only=False)
        serializer = DeviceTokenSerializer(tokens, many=True)
        return success_response(data=serializer.data)

    def post(self, request):
        serializer = DeviceTokenRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device_token, created = DeviceTokenService.register(
            user=request.user,
            token=serializer.validated_data["token"],
            platform=serializer.validated_data["platform"],
        )
        response_serializer = DeviceTokenSerializer(device_token)
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        message = "Device token registered." if created else "Device token updated."
        return success_response(
            data=response_serializer.data, message=message, status=response_status
        )


class DeviceTokenDeactivateView(APIView):
    """POST /api/v1/notifications/device-tokens/{id}/deactivate/

    No DELETE endpoint exists for DeviceToken anywhere in this app — DDS
    §4.16/§9.9 documents deactivation, not deletion, as the invalidation
    path ("for audit trail").
    """

    permission_classes = [IsAuthenticatedCustomer]

    def post(self, request, pk):
        device_token = get_object_or_404(
            DeviceToken.objects.alive().filter(user=request.user), pk=pk
        )
        device_token = DeviceTokenService.deactivate(
            device_token=device_token, user=request.user
        )
        serializer = DeviceTokenSerializer(device_token)
        return success_response(
            data=serializer.data, message="Device token deactivated."
        )
