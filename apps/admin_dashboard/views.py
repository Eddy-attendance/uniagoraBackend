from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from apps.common.openapi import (
    list_response_schema,
    paginated_response_schema,
    success_response_schema,
)
from apps.common.pagination import StandardResultsSetPagination
from apps.common.response import success_response
from apps.core.permissions import IsAdmin
from apps.reports.serializers import ReportAdminSerializer

from .serializers import (
    AdminCategorySerializer,
    AdminCategoryUpdateSerializer,
    AdminCategoryWriteSerializer,
    AdminProductSerializer,
    AdminResolutionSerializer,
    AdminUserSerializer,
    AdminVendorSerializer,
    DashboardSummarySerializer,
)
from .services import (
    AdminCategoryService,
    AdminProductService,
    AdminReportService,
    AdminUserService,
    AdminVendorService,
    DashboardService,
)


class DashboardSummaryView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        responses={
            200: success_response_schema(
                "DashboardSummaryResponse",
                DashboardSummarySerializer,
            ),
        },
    )
    def get(self, request):
        data = DashboardService.get_summary()
        serializer = DashboardSummarySerializer(data)

        return success_response(
            data=serializer.data,
            message="",
        )


class AdminUserListView(APIView):
    permission_classes = [IsAdmin]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        operation_id="admin_users_list",
        responses={
            200: paginated_response_schema(
                "AdminUserListResponse",
                AdminUserSerializer,
            ),
        },
    )
    def get(self, request):
        qs = AdminUserService.get_queryset().order_by("-created_at")

        is_active = request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = AdminUserSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)


class AdminUserDetailView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="admin_users_retrieve",
        responses={
            200: success_response_schema(
                "AdminUserDetailResponse",
                AdminUserSerializer,
            ),
        },
    )
    def get(self, request, id):
        user = AdminUserService.get(user_id=id)

        return success_response(
            data=AdminUserSerializer(user).data,
            message="",
        )


class AdminUserActivateView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        request=None,
        responses={
            200: success_response_schema(
                "AdminUserActivateResponse",
                AdminUserSerializer,
            ),
        },
    )
    def post(self, request, id):
        user = AdminUserService.activate(
            user=AdminUserService.get(user_id=id),
        )

        return success_response(
            data=AdminUserSerializer(user).data,
            message="User activated.",
        )


class AdminUserDeactivateView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        request=None,
        responses={
            200: success_response_schema(
                "AdminUserDeactivateResponse",
                AdminUserSerializer,
            ),
        },
    )
    def post(self, request, id):
        user = AdminUserService.deactivate(
            user=AdminUserService.get(user_id=id),
        )

        return success_response(
            data=AdminUserSerializer(user).data,
            message="User deactivated.",
        )


class AdminVendorListView(APIView):
    permission_classes = [IsAdmin]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        operation_id="admin_vendors_list",
        responses={
            200: paginated_response_schema(
                "AdminVendorListResponse",
                AdminVendorSerializer,
            ),
        },
    )
    def get(self, request):
        qs = AdminVendorService.get_queryset().order_by("-created_at")

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = AdminVendorSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)


class AdminVendorDetailView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="admin_vendors_retrieve",
        responses={
            200: success_response_schema(
                "AdminVendorDetailResponse",
                AdminVendorSerializer,
            ),
        },
    )
    def get(self, request, id):
        vendor = AdminVendorService.get(vendor_id=id)

        return success_response(
            data=AdminVendorSerializer(vendor).data,
            message="",
        )


class AdminVendorSuspendView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        request=None,
        responses={
            200: success_response_schema(
                "AdminVendorSuspendResponse",
                AdminVendorSerializer,
            ),
        },
    )
    def post(self, request, id):
        vendor = AdminVendorService.suspend(
            vendor_profile=AdminVendorService.get(vendor_id=id),
        )

        return success_response(
            data=AdminVendorSerializer(vendor).data,
            message="Vendor suspended.",
        )


class AdminVendorReinstateView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        request=None,
        responses={
            200: success_response_schema(
                "AdminVendorReinstateResponse",
                AdminVendorSerializer,
            ),
        },
    )
    def post(self, request, id):
        vendor = AdminVendorService.reinstate(
            vendor_profile=AdminVendorService.get(vendor_id=id),
        )

        return success_response(
            data=AdminVendorSerializer(vendor).data,
            message="Vendor reinstated.",
        )


class AdminProductListView(APIView):
    permission_classes = [IsAdmin]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        operation_id="admin_products_list",
        responses={
            200: paginated_response_schema(
                "AdminProductListResponse",
                AdminProductSerializer,
            ),
        },
    )
    def get(self, request):
        qs = AdminProductService.get_queryset().order_by("-listed_at")

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = AdminProductSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)


class AdminProductDetailView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="admin_products_retrieve",
        responses={
            200: success_response_schema(
                "AdminProductDetailResponse",
                AdminProductSerializer,
            ),
        },
    )
    def get(self, request, id):
        product = AdminProductService.get(product_id=id)

        return success_response(
            data=AdminProductSerializer(product).data,
            message="",
        )


class AdminProductRemoveView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        request=None,
        responses={
            200: success_response_schema(
                "AdminProductRemoveResponse",
                AdminProductSerializer,
            ),
        },
    )
    def post(self, request, id):
        product = AdminProductService.remove(
            product=AdminProductService.get(product_id=id),
        )

        return success_response(
            data=AdminProductSerializer(product).data,
            message="Product removed.",
        )


class AdminCategoryListCreateView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="admin_categories_list",
        responses={
            200: list_response_schema(
                "AdminCategoryListResponse",
                AdminCategorySerializer,
            ),
        },
    )
    def get(self, request):
        qs = AdminCategoryService.get_queryset(
            parent=request.query_params.get("parent"),
        ).order_by("display_order", "name")

        return success_response(
            data=AdminCategorySerializer(qs, many=True).data,
            message="",
        )

    @extend_schema(
        request=AdminCategoryWriteSerializer,
        responses={
            201: success_response_schema(
                "AdminCategoryCreatedResponse",
                AdminCategorySerializer,
            ),
        },
    )
    def post(self, request):
        serializer = AdminCategoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        category = AdminCategoryService.create(
            **serializer.validated_data,
        )

        return success_response(
            data=AdminCategorySerializer(category).data,
            message="Category created.",
            status=201,
        )


class AdminCategoryDetailView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="admin_categories_retrieve",
        responses={
            200: success_response_schema(
                "AdminCategoryDetailResponse",
                AdminCategorySerializer,
            ),
        },
    )
    def get(self, request, slug):
        category = AdminCategoryService.get(slug=slug)

        return success_response(
            data=AdminCategorySerializer(category).data,
            message="",
        )

    @extend_schema(
        request=AdminCategoryUpdateSerializer,
        responses={
            200: success_response_schema(
                "AdminCategoryUpdateResponse",
                AdminCategorySerializer,
            ),
        },
    )
    def patch(self, request, slug):
        category = AdminCategoryService.get(slug=slug)

        serializer = AdminCategoryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        category = AdminCategoryService.update(
            category=category,
            **serializer.validated_data,
        )

        return success_response(
            data=AdminCategorySerializer(category).data,
            message="Category updated.",
        )

    @extend_schema(
        responses=None,
    )
    def delete(self, request, slug):
        AdminCategoryService.delete(
            category=AdminCategoryService.get(slug=slug),
        )

        return success_response(
            data=None,
            message="Category deleted.",
            status=204,
        )


class AdminCategoryActivateView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        request=None,
        responses={
            200: success_response_schema(
                "AdminCategoryActivateResponse",
                AdminCategorySerializer,
            ),
        },
    )
    def post(self, request, slug):
        category = AdminCategoryService.activate(
            category=AdminCategoryService.get(slug=slug),
        )

        return success_response(
            data=AdminCategorySerializer(category).data,
            message="Category activated.",
        )


class AdminCategoryDeactivateView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        request=None,
        responses={
            200: success_response_schema(
                "AdminCategoryDeactivateResponse",
                AdminCategorySerializer,
            ),
        },
    )
    def post(self, request, slug):
        category = AdminCategoryService.deactivate(
            category=AdminCategoryService.get(slug=slug),
        )

        return success_response(
            data=AdminCategorySerializer(category).data,
            message="Category deactivated.",
        )


class AdminReportListView(APIView):
    permission_classes = [IsAdmin]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        operation_id="admin_reports_list",
        responses={
            200: paginated_response_schema(
                "AdminReportListResponse",
                ReportAdminSerializer,
            ),
        },
    )
    def get(self, request):
        qs = AdminReportService.get_queryset(
            status=request.query_params.get("status"),
        ).order_by("created_at")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = ReportAdminSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)


class AdminReportDetailView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        operation_id="admin_reports_retrieve",
        responses={
            200: success_response_schema(
                "AdminReportDetailResponse",
                ReportAdminSerializer,
            ),
        },
    )
    def get(self, request, id):
        report = AdminReportService.get(report_id=id)

        return success_response(
            data=ReportAdminSerializer(report).data,
            message="",
        )


class AdminReportUnderReviewView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        request=None,
        responses={
            200: success_response_schema(
                "AdminReportUnderReviewResponse",
                ReportAdminSerializer,
            ),
        },
    )
    def post(self, request, id):
        report = AdminReportService.mark_under_review(
            report=AdminReportService.get(report_id=id),
        )

        return success_response(
            data=ReportAdminSerializer(report).data,
            message="Report marked under review.",
        )


class AdminReportResolveView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        request=AdminResolutionSerializer,
        responses={
            200: success_response_schema(
                "AdminReportResolveResponse",
                ReportAdminSerializer,
            ),
        },
    )
    def post(self, request, id):
        report = AdminReportService.get(report_id=id)

        serializer = AdminResolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report = AdminReportService.resolve(
            report=report,
            admin_user=request.user,
            resolution_notes=serializer.validated_data.get("resolution_notes"),
        )

        return success_response(
            data=ReportAdminSerializer(report).data,
            message="Report resolved.",
        )


class AdminReportRejectView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        request=AdminResolutionSerializer,
        responses={
            200: success_response_schema(
                "AdminReportRejectResponse",
                ReportAdminSerializer,
            ),
        },
    )
    def post(self, request, id):
        report = AdminReportService.get(report_id=id)

        serializer = AdminResolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report = AdminReportService.reject(
            report=report,
            admin_user=request.user,
            resolution_notes=serializer.validated_data.get("resolution_notes"),
        )

        return success_response(
            data=ReportAdminSerializer(report).data,
            message="Report rejected.",
        )
