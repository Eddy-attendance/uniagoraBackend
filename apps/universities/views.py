from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action

from apps.common.openapi import (
    paginated_response_schema,
    success_response_schema,
)
from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.core.permissions import IsAdmin, IsAuthenticatedCustomer

from .models import University
from .serializers import UniversityAdminWriteSerializer, UniversitySerializer
from .services import UniversityService


class UniversityViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "slug"
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        if self.action in ("list", "retrieve"):
            return University.objects.active()
        return University.objects.alive()

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticatedCustomer()]
        return [IsAdmin()]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return UniversityAdminWriteSerializer
        return UniversitySerializer

    @extend_schema(
        summary="List supported universities (onboarding dropdown).",
        request=None,
        responses={
            200: paginated_response_schema(
                "UniversityListResponse", UniversitySerializer
            ),
        },
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        request=None,
        responses={
            200: success_response_schema(
                "UniversityDetailResponse", UniversitySerializer
            ),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(data=serializer.data)

    @extend_schema(
        summary="Create a university (admin).",
        request=UniversityAdminWriteSerializer,
        responses={
            201: OpenApiResponse(
                success_response_schema(
                    "UniversityCreateResponse", UniversitySerializer
                ),
                description="University created.",
            ),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        university = UniversityService.create(**serializer.validated_data)
        output = UniversitySerializer(university)
        return success_response(data=output.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Update a university (admin).",
        request=UniversityAdminWriteSerializer,
        responses={
            200: success_response_schema(
                "UniversityUpdateResponse", UniversitySerializer
            ),
        },
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        university = UniversityService.update(
            university=instance, **serializer.validated_data
        )
        output = UniversitySerializer(university)
        return success_response(data=output.data)

    @extend_schema(
        request=UniversityAdminWriteSerializer,
        responses={
            200: success_response_schema(
                "UniversityPartialUpdateResponse", UniversitySerializer
            ),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @extend_schema(
        request=None,
        responses={
            200: success_response_schema(
                "UniversityActivateResponse", UniversitySerializer
            ),
        },
    )
    @action(detail=True, methods=["post"])
    def activate(self, request, *args, **kwargs):
        instance = self.get_object()
        university = UniversityService.activate(university=instance)
        return success_response(data=UniversitySerializer(university).data)

    @extend_schema(
        request=None,
        responses={
            200: success_response_schema(
                "UniversityDeactivateResponse", UniversitySerializer
            ),
        },
    )
    @action(detail=True, methods=["post"])
    def deactivate(self, request, *args, **kwargs):
        instance = self.get_object()
        university = UniversityService.deactivate(university=instance)
        return success_response(data=UniversitySerializer(university).data)
