from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action

from apps.common.exceptions import NotFoundError
from apps.common.response import success_response
from apps.core.permissions import IsAdmin, IsAuthenticatedCustomer

from .models import VendorProfile
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

    @action(detail=False, methods=["get"])
    def me(self, request):
        vendor_profile = getattr(request.user, "vendor_profile", None)
        if vendor_profile is None:
            raise NotFoundError("You do not have a vendor profile.")
        return success_response(data=VendorProfileSerializer(vendor_profile).data)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        vendor_profile = self.get_object()
        vendor_profile = VendorSuspensionService.suspend(vendor_profile=vendor_profile)
        return success_response(data=VendorProfileSerializer(vendor_profile).data)

    @action(detail=True, methods=["post"])
    def reinstate(self, request, pk=None):
        vendor_profile = self.get_object()
        vendor_profile = VendorSuspensionService.reinstate(
            vendor_profile=vendor_profile
        )
        return success_response(data=VendorProfileSerializer(vendor_profile).data)
