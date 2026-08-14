"""
apps/admin_dashboard/views.py

Every view is deliberately thin: resolve a target via the matching
*Service.get(...)* (raises NotFoundError -> 404 through the shared
exception handler), delegate any mutation to services.py, serialize,
return via common.response.success_response(). No business rule is
evaluated in this file. All endpoints are gated by core.permissions
.IsAdmin only — no second permission/role system is introduced anywhere
in this app.
"""

from rest_framework.views import APIView

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

# --------------------------------------------------------------- Dashboard


class DashboardSummaryView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        data = DashboardService.get_summary()
        serializer = DashboardSummarySerializer(data)
        return success_response(data=serializer.data, message="")


# ------------------------------------------------------------------- Users


class AdminUserListView(APIView):
    permission_classes = [IsAdmin]
    pagination_class = StandardResultsSetPagination

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

    def get(self, request, id):
        user = AdminUserService.get(user_id=id)
        return success_response(data=AdminUserSerializer(user).data, message="")


class AdminUserActivateView(APIView):
    """Orchestration only. The actual `is_active` mutation and its
    conflict guard live in apps.users.services.UserService.activate() —
    see services.py::AdminUserService.activate()."""

    permission_classes = [IsAdmin]

    def post(self, request, id):
        user = AdminUserService.activate(user=AdminUserService.get(user_id=id))
        return success_response(
            data=AdminUserSerializer(user).data, message="User activated."
        )


class AdminUserDeactivateView(APIView):
    """Orchestration only. The actual `is_active` mutation and its
    conflict guard live in apps.users.services.UserService.deactivate()
    — see services.py::AdminUserService.deactivate()."""

    permission_classes = [IsAdmin]

    def post(self, request, id):
        user = AdminUserService.deactivate(user=AdminUserService.get(user_id=id))
        return success_response(
            data=AdminUserSerializer(user).data, message="User deactivated."
        )


# ----------------------------------------------------------------- Vendors


class AdminVendorListView(APIView):
    permission_classes = [IsAdmin]
    pagination_class = StandardResultsSetPagination

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

    def get(self, request, id):
        vendor = AdminVendorService.get(vendor_id=id)
        return success_response(data=AdminVendorSerializer(vendor).data, message="")


class AdminVendorSuspendView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, id):
        vendor = AdminVendorService.suspend(
            vendor_profile=AdminVendorService.get(vendor_id=id)
        )
        return success_response(
            data=AdminVendorSerializer(vendor).data, message="Vendor suspended."
        )


class AdminVendorReinstateView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, id):
        vendor = AdminVendorService.reinstate(
            vendor_profile=AdminVendorService.get(vendor_id=id)
        )
        return success_response(
            data=AdminVendorSerializer(vendor).data, message="Vendor reinstated."
        )


# ---------------------------------------------------------------- Products


class AdminProductListView(APIView):
    permission_classes = [IsAdmin]
    pagination_class = StandardResultsSetPagination

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

    def get(self, request, id):
        product = AdminProductService.get(product_id=id)
        return success_response(data=AdminProductSerializer(product).data, message="")


class AdminProductRemoveView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, id):
        product = AdminProductService.remove(
            product=AdminProductService.get(product_id=id)
        )
        return success_response(
            data=AdminProductSerializer(product).data, message="Product removed."
        )


# -------------------------------------------------------------- Categories


class AdminCategoryListCreateView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        qs = AdminCategoryService.get_queryset(
            parent=request.query_params.get("parent")
        ).order_by("display_order", "name")
        return success_response(
            data=AdminCategorySerializer(qs, many=True).data, message=""
        )

    def post(self, request):
        serializer = AdminCategoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = AdminCategoryService.create(**serializer.validated_data)
        return success_response(
            data=AdminCategorySerializer(category).data,
            message="Category created.",
            status=201,
        )


class AdminCategoryDetailView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, slug):
        category = AdminCategoryService.get(slug=slug)
        return success_response(data=AdminCategorySerializer(category).data, message="")

    def patch(self, request, slug):
        category = AdminCategoryService.get(slug=slug)
        serializer = AdminCategoryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = AdminCategoryService.update(
            category=category, **serializer.validated_data
        )
        return success_response(
            data=AdminCategorySerializer(category).data, message="Category updated."
        )

    def delete(self, request, slug):
        AdminCategoryService.delete(category=AdminCategoryService.get(slug=slug))
        return success_response(data=None, message="Category deleted.", status=204)


class AdminCategoryActivateView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, slug):
        category = AdminCategoryService.activate(
            category=AdminCategoryService.get(slug=slug)
        )
        return success_response(
            data=AdminCategorySerializer(category).data, message="Category activated."
        )


class AdminCategoryDeactivateView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, slug):
        category = AdminCategoryService.deactivate(
            category=AdminCategoryService.get(slug=slug)
        )
        return success_response(
            data=AdminCategorySerializer(category).data, message="Category deactivated."
        )


# ---------------------------------------------------------------- Reports


class AdminReportListView(APIView):
    permission_classes = [IsAdmin]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        qs = AdminReportService.get_queryset(
            status=request.query_params.get("status")
        ).order_by("created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = ReportAdminSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminReportDetailView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, id):
        report = AdminReportService.get(report_id=id)
        return success_response(data=ReportAdminSerializer(report).data, message="")


class AdminReportUnderReviewView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, id):
        report = AdminReportService.mark_under_review(
            report=AdminReportService.get(report_id=id)
        )
        return success_response(
            data=ReportAdminSerializer(report).data,
            message="Report marked under review.",
        )


class AdminReportResolveView(APIView):
    permission_classes = [IsAdmin]

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
            data=ReportAdminSerializer(report).data, message="Report resolved."
        )


class AdminReportRejectView(APIView):
    permission_classes = [IsAdmin]

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
            data=ReportAdminSerializer(report).data, message="Report rejected."
        )
