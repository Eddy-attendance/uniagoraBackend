"""
Store views — thin, service-delegating.

Routing:
`me` is registered as a `detail=False` DRF router action so that
`/stores/me/` is resolved before the `{slug}` detail route.

The agreed API contract is preserved:

POST   /api/v1/stores/         IsVerifiedVendor         create
GET    /api/v1/stores/{slug}/  IsAuthenticatedCustomer  retrieve
GET    /api/v1/stores/me/      IsAuthenticatedCustomer  own store
PATCH  /api/v1/stores/me/      IsAuthenticatedCustomer  update own store
DELETE /api/v1/stores/me/      IsAuthenticatedCustomer  soft-delete own store

No `list` action is defined. GET /stores/ therefore remains unbound
rather than exposing an unintended collection endpoint.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action

from apps.common.exceptions import NotFoundError
from apps.common.response import success_response
from apps.core.permissions import IsAuthenticatedCustomer, IsVerifiedVendor

from .models import Store
from .serializers import StoreSerializer, StoreWriteSerializer
from .services import StoreService


class StoreViewSet(viewsets.GenericViewSet):
    queryset = Store.objects.alive()
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_permissions(self):
        if self.action == "create":
            return [IsVerifiedVendor()]

        return [IsAuthenticatedCustomer()]

    def get_queryset(self):
        if self.action == "retrieve":
            return Store.objects.alive().filter(is_active=True)

        return Store.objects.alive()

    def create(self, request, *args, **kwargs):
        serializer = StoreWriteSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        store = StoreService.create(
            vendor_profile=request.user.vendor_profile,
            **serializer.validated_data,
        )

        output = StoreSerializer(
            store,
            context={"request": request},
        )

        return success_response(
            data=output.data,
            message="Store created.",
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = StoreSerializer(
            instance,
            context={"request": request},
        )

        return success_response(data=serializer.data)

    @action(
        detail=False,
        methods=["get", "patch", "delete"],
        url_path="me",
    )
    def me(self, request, *args, **kwargs):
        store = self._get_own_store(request)

        if request.method == "GET":
            serializer = StoreSerializer(
                store,
                context={"request": request},
            )

            return success_response(data=serializer.data)

        if request.method == "PATCH":
            serializer = StoreWriteSerializer(
                store,
                data=request.data,
                partial=True,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)

            updated = StoreService.update(
                store=store,
                **serializer.validated_data,
            )

            output = StoreSerializer(
                updated,
                context={"request": request},
            )

            return success_response(
                data=output.data,
                message="Store updated.",
            )

        StoreService.delete(store=store)

        return success_response(
            message="Store deleted.",
        )

    @staticmethod
    def _get_own_store(request):
        """
        Resolve the requester's own store.

        Ownership is derived exclusively from request.user rather than
        any client-supplied identifier
        """
        vendor_profile = getattr(request.user, "vendor_profile", None)

        if vendor_profile is None:
            raise NotFoundError("You do not have a store.")

        try:
            store = vendor_profile.store
        except Store.DoesNotExist:
            raise NotFoundError("You do not have a store.") from None

        if store.is_deleted:
            raise NotFoundError("You do not have a store.")

        return store
