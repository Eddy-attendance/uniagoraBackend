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

    `?unread=true` narrows to unread-only
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
    """GET/POST /api/v1/notifications/device-tokens/"""

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
    """POST /api/v1/notifications/device-tokens/{id}/deactivate/"""

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
