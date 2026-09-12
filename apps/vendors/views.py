from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action

from apps.common.exceptions import NotFoundError
from apps.common.openapi import paginated_response_schema, success_response_schema
from apps.common.response import success_response
from apps.core.permissions import IsAdmin, IsAuthenticatedCustomer

from .models import VendorProfile, VendorStatus
from .serializers import VendorApplicationSerializer, VendorProfileSerializer
from .services import VendorApplicationService, VendorSuspensionService


class VendorProfileViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    POST   /vendors/               apply (Customer)               -> auto-verified
    GET    /vendors/                list (Admin)                  -> vendor queue
    GET    /vendors/{id}/           retrieve (Admin)
    GET    /vendors/me/             own profile (Customer)
    POST   /vendors/{id}/suspend/   Admin
    POST   /vendors/{id}/reinstate/ Admin
    """

    queryset = VendorProfile.objects.alive().select_related("university", "reviewed_by")
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return VendorApplicationSerializer
        return VendorProfileSerializer

    def get_permissions(self):
        if self.action in ("create", "me"):
            return [IsAuthenticatedCustomer()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    @extend_schema(
        summary="Apply to become a vendor (auto-approved in MVP).",
        request=VendorApplicationSerializer,
        responses={
            201: OpenApiResponse(
                success_response_schema(
                    "VendorApplicationResponse", VendorProfileSerializer
                ),
                description="Application submitted and auto-approved (MVP).",
            ),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vendor_profile = VendorApplicationService.apply(
            user=request.user, **serializer.validated_data
        )
        output = VendorProfileSerializer(vendor_profile).data
        return success_response(
            data=output,
            message="Vendor application submitted and approved.",
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="List vendor profiles (admin verification queue).",
        parameters=[
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=VendorStatus.values,
                description="Filter vendor profiles by status.",
            ),
        ],
        request=None,
        responses={
            200: paginated_response_schema(
                "VendorProfileListResponse", VendorProfileSerializer
            ),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a vendor profile (admin).",
        request=None,
        responses={
            200: success_response_schema(
                "VendorProfileDetailResponse", VendorProfileSerializer
            ),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        """Admin retrieval of any vendor profile (verification/audit)."""
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve the authenticated user's own vendor profile.",
        request=None,
        responses={
            200: success_response_schema(
                "VendorProfileMeResponse", VendorProfileSerializer
            ),
        },
    )
    @action(detail=False, methods=["get"])
    def me(self, request):
        vendor_profile = getattr(request.user, "vendor_profile", None)
        if vendor_profile is None:
            raise NotFoundError("You do not have a vendor profile.")
        return success_response(data=VendorProfileSerializer(vendor_profile).data)

    @extend_schema(
        summary="Suspend a vendor (admin; hides store and listings).",
        request=None,
        responses={
            200: success_response_schema(
                "VendorSuspendResponse", VendorProfileSerializer
            ),
        },
    )
    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        vendor_profile = self.get_object()
        vendor_profile = VendorSuspensionService.suspend(vendor_profile=vendor_profile)
        return success_response(data=VendorProfileSerializer(vendor_profile).data)

    @extend_schema(
        summary="Reinstate a suspended vendor (admin).",
        request=None,
        responses={
            200: success_response_schema(
                "VendorReinstateResponse", VendorProfileSerializer
            ),
        },
    )
    @action(detail=True, methods=["post"])
    def reinstate(self, request, pk=None):
        vendor_profile = self.get_object()
        vendor_profile = VendorSuspensionService.reinstate(
            vendor_profile=vendor_profile
        )
        return success_response(data=VendorProfileSerializer(vendor_profile).data)
