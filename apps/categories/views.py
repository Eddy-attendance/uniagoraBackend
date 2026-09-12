from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.openapi import (
    paginated_response_schema,
    success_response_schema,
)
from apps.common.response import success_response
from apps.core.permissions import IsAdmin, IsAuthenticatedCustomer

from .models import Category
from .serializers import (
    CategoryCreateSerializer,
    CategorySerializer,
    CategoryUpdateSerializer,
)
from .services import CategoryService


class CategoryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        if self.action in ("list", "retrieve"):
            queryset = Category.objects.visible()
        else:
            queryset = Category.objects.alive()

        if self.action == "list":
            parent_slug = self.request.query_params.get("parent")
            if parent_slug is not None:
                if parent_slug.strip().lower() in ("", "null", "none"):
                    queryset = queryset.filter(parent__isnull=True)
                else:
                    queryset = queryset.filter(parent__slug=parent_slug)

        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return CategoryCreateSerializer
        if self.action in ("update", "partial_update"):
            return CategoryUpdateSerializer
        return CategorySerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            permission_classes = [IsAuthenticatedCustomer]
        else:
            permission_classes = [IsAdmin]
        return [permission() for permission in permission_classes]

    @extend_schema(
        summary="Browse the active category tree (customer-facing).",
        parameters=[
            OpenApiParameter(
                name="parent",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filter children by parent category slug. Pass 'null' "
                    "(or leave empty) to list root categories."
                ),
            )
        ],
        request=None,
        responses={
            200: paginated_response_schema("CategoryListResponse", CategorySerializer),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        request=None,
        responses={
            200: success_response_schema("CategoryDetailResponse", CategorySerializer),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Create a category (admin).",
        request=CategoryCreateSerializer,
        responses={
            201: OpenApiResponse(
                success_response_schema("CategoryCreateResponse", CategorySerializer),
                description="Category created.",
            ),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = CategoryService.create(**serializer.validated_data)
        return success_response(
            data=CategorySerializer(category).data,
            message="Category created.",
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Update a category (admin).",
        request=CategoryUpdateSerializer,
        responses={
            200: success_response_schema("CategoryUpdateResponse", CategorySerializer),
        },
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        category = CategoryService.update(
            category=instance, **serializer.validated_data
        )
        return success_response(
            data=CategorySerializer(category).data,
            message="Category updated.",
        )

    @extend_schema(
        request=CategoryUpdateSerializer,
        responses={
            200: success_response_schema(
                "CategoryPartialUpdateResponse", CategorySerializer
            ),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @extend_schema(
        summary="Soft-delete a category (admin).",
        responses={204: None},
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        CategoryService.delete(category=instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=None,
        responses={
            200: success_response_schema(
                "CategoryActivateResponse", CategorySerializer
            ),
        },
    )
    @action(detail=True, methods=["post"])
    def activate(self, request, *args, **kwargs):
        instance = self.get_object()
        category = CategoryService.activate(category=instance)
        return success_response(
            data=CategorySerializer(category).data,
            message="Category activated.",
        )

    @extend_schema(
        request=None,
        responses={
            200: success_response_schema(
                "CategoryDeactivateResponse", CategorySerializer
            ),
        },
    )
    @action(detail=True, methods=["post"])
    def deactivate(self, request, *args, **kwargs):
        instance = self.get_object()
        category = CategoryService.deactivate(category=instance)
        return success_response(
            data=CategorySerializer(category).data,
            message="Category deactivated.",
        )
