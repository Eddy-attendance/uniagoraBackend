from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = CategoryService.create(**serializer.validated_data)
        return Response(
            CategorySerializer(category).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        category = CategoryService.update(
            category=instance, **serializer.validated_data
        )
        return Response(CategorySerializer(category).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        CategoryService.delete(category=instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def activate(self, request, *args, **kwargs):
        instance = self.get_object()
        category = CategoryService.activate(category=instance)
        return Response(CategorySerializer(category).data)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, *args, **kwargs):
        instance = self.get_object()
        category = CategoryService.deactivate(category=instance)
        return Response(CategorySerializer(category).data)
