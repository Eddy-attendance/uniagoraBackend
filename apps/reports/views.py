from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView

from apps.common.openapi import (
    paginated_response_schema,
    success_response_schema,
)
from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.core.permissions import IsAdmin, IsAuthenticatedCustomer
from apps.products.models import Product
from apps.vendors.models import VendorProfile

from .models import Report, ReportStatus
from .permissions import IsReportOwnerOrAdmin
from .serializers import (
    ReportAdminSerializer,
    ReportCreateSerializer,
    ReportResolutionSerializer,
    ReportSerializer,
)
from .services import ReportService


class ReportProductCreateView(APIView):
    """POST /api/v1/reports/products/{product_id}/"""

    permission_classes = [IsAuthenticatedCustomer]

    @extend_schema(
        request=ReportCreateSerializer,
        responses={
            status.HTTP_201_CREATED: success_response_schema(
                "ProductReportCreateResponse",
                ReportSerializer,
            ),
        },
    )
    def post(self, request, product_id):
        product = get_object_or_404(
            Product.objects.alive(),
            pk=product_id,
        )

        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report = ReportService.create_for_product(
            reporter=request.user,
            product=product,
            **serializer.validated_data,
        )

        return success_response(
            data=ReportSerializer(report).data,
            message="Product reported.",
            status=status.HTTP_201_CREATED,
        )


class ReportVendorCreateView(APIView):
    """POST /api/v1/reports/vendors/{vendor_id}/"""

    permission_classes = [IsAuthenticatedCustomer]

    @extend_schema(
        request=ReportCreateSerializer,
        responses={
            status.HTTP_201_CREATED: success_response_schema(
                "VendorReportCreateResponse",
                ReportSerializer,
            ),
        },
    )
    def post(self, request, vendor_id):
        vendor_profile = get_object_or_404(
            VendorProfile.objects.alive(),
            pk=vendor_id,
        )

        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report = ReportService.create_for_vendor(
            reporter=request.user,
            vendor_profile=vendor_profile,
            **serializer.validated_data,
        )

        return success_response(
            data=ReportSerializer(report).data,
            message="Vendor reported.",
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    responses={
        status.HTTP_200_OK: paginated_response_schema(
            "MyReportsListResponse",
            ReportSerializer,
        ),
    },
)
class MyReportsListView(generics.ListAPIView):
    """GET /api/v1/reports/mine/."""

    permission_classes = [IsAuthenticatedCustomer]
    serializer_class = ReportSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return (
            Report.objects.alive()
            .filter(reporter=self.request.user)
            .select_related(
                "product",
                "vendor_profile",
            )
            .order_by("-created_at")
        )


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="status",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            enum=ReportStatus.values,
            description="Filter reports by moderation status.",
        ),
    ],
    responses={
        status.HTTP_200_OK: paginated_response_schema(
            "ReportsAdminListResponse",
            ReportAdminSerializer,
        ),
    },
)
class ReportAdminListView(generics.ListAPIView):
    """GET /api/v1/reports/."""

    permission_classes = [IsAdmin]
    serializer_class = ReportAdminSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = (
            Report.objects.alive()
            .select_related(
                "reporter",
                "resolved_by",
                "product",
                "vendor_profile",
            )
            .order_by("created_at")
        )

        status_param = self.request.query_params.get("status")

        if status_param:
            if status_param not in ReportStatus.values:
                raise ValidationError({"status": "Invalid status filter."})

            queryset = queryset.filter(status=status_param)

        return queryset


@extend_schema(
    responses={
        status.HTTP_200_OK: success_response_schema(
            "ReportDetailResponse",
            ReportSerializer,
        ),
    },
)
class ReportDetailView(generics.RetrieveAPIView):
    """GET /api/v1/reports/{report_id}/."""

    permission_classes = [
        IsAuthenticatedCustomer,
        IsReportOwnerOrAdmin,
    ]

    queryset = Report.objects.alive().select_related(
        "reporter",
        "resolved_by",
        "product",
        "vendor_profile",
    )

    lookup_url_kwarg = "report_id"

    def get_serializer_class(self):
        user = self.request.user

        if user.is_staff or user.is_superuser:
            return ReportAdminSerializer

        return ReportSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return success_response(
            data=serializer.data,
            message="Report retrieved successfully.",
        )


class ReportUnderReviewView(APIView):
    """POST /api/v1/reports/{report_id}/under-review/."""

    permission_classes = [IsAdmin]

    @extend_schema(
        request=None,
        responses={
            status.HTTP_200_OK: success_response_schema(
                "ReportUnderReviewResponse",
                ReportAdminSerializer,
            ),
        },
    )
    def post(self, request, report_id):
        report = get_object_or_404(
            Report.objects.alive(),
            pk=report_id,
        )

        report = ReportService.mark_under_review(
            report=report,
        )

        return success_response(
            data=ReportAdminSerializer(report).data,
            message="Report moved to under review.",
        )


class ReportResolveView(APIView):
    """POST /api/v1/reports/{report_id}/resolve/."""

    permission_classes = [IsAdmin]

    @extend_schema(
        request=ReportResolutionSerializer,
        responses={
            status.HTTP_200_OK: success_response_schema(
                "ReportResolveResponse",
                ReportAdminSerializer,
            ),
        },
    )
    def post(self, request, report_id):
        report = get_object_or_404(
            Report.objects.alive(),
            pk=report_id,
        )

        serializer = ReportResolutionSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        report = ReportService.resolve(
            report=report,
            admin=request.user,
            resolution_notes=serializer.validated_data.get(
                "resolution_notes",
            ),
        )

        return success_response(
            data=ReportAdminSerializer(report).data,
            message="Report resolved.",
        )


class ReportRejectView(APIView):
    """POST /api/v1/reports/{report_id}/reject/."""

    permission_classes = [IsAdmin]

    @extend_schema(
        request=ReportResolutionSerializer,
        responses={
            status.HTTP_200_OK: success_response_schema(
                "ReportRejectResponse",
                ReportAdminSerializer,
            ),
        },
    )
    def post(self, request, report_id):
        report = get_object_or_404(
            Report.objects.alive(),
            pk=report_id,
        )

        serializer = ReportResolutionSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        report = ReportService.reject(
            report=report,
            admin=request.user,
            resolution_notes=serializer.validated_data.get(
                "resolution_notes",
            ),
        )

        return success_response(
            data=ReportAdminSerializer(report).data,
            message="Report rejected.",
        )
