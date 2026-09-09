from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.views import APIView

from apps.common.openapi import success_response_schema
from apps.common.response import success_response
from apps.core.permissions import IsAuthenticatedCustomer

from .serializers import (
    SetActiveUniversitySerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from .services import UserService


class MeView(APIView):
    """GET/PATCH the authenticated user's own profile."""

    permission_classes = [IsAuthenticatedCustomer]

    @extend_schema(
        responses={
            status.HTTP_200_OK: success_response_schema(
                "CurrentUserResponse",
                UserSerializer,
            ),
        },
    )
    def get(self, request):
        return success_response(
            data=UserSerializer(request.user).data,
        )

    @extend_schema(
        request=UserUpdateSerializer,
        responses={
            status.HTTP_200_OK: success_response_schema(
                "UserUpdateResponse",
                UserSerializer,
            ),
        },
    )
    def patch(self, request):
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        user = UserService.update_profile(
            user=request.user,
            **serializer.validated_data,
        )

        return success_response(
            data=UserSerializer(user).data,
        )


class SetActiveUniversityView(APIView):
    """
    PATCH /users/me/active-university/
    Change the user's active university.
    """

    permission_classes = [IsAuthenticatedCustomer]

    @extend_schema(
        request=SetActiveUniversitySerializer,
        responses={
            status.HTTP_200_OK: success_response_schema(
                "SetActiveUniversityResponse",
                UserSerializer,
            ),
        },
    )
    def patch(self, request):
        serializer = SetActiveUniversitySerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        user = UserService.set_active_university(
            user=request.user,
            university=serializer.validated_data["university_slug"],
        )

        return success_response(
            data=UserSerializer(user).data,
        )
