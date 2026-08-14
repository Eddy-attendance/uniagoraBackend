"""
apps/admin_dashboard/urls.py

Mount in the project root URL configuration as:

    path("api/v1/admin/", include("apps.admin_dashboard.urls")),

Not this app's file to own/edit (root urls.py belongs to config/).
"""

from django.urls import path

from . import views

app_name = "admin_dashboard"

urlpatterns = [
    path("dashboard/", views.DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("users/", views.AdminUserListView.as_view(), name="user-list"),
    path("users/<uuid:id>/", views.AdminUserDetailView.as_view(), name="user-detail"),
    path(
        "users/<uuid:id>/activate/",
        views.AdminUserActivateView.as_view(),
        name="user-activate",
    ),
    path(
        "users/<uuid:id>/deactivate/",
        views.AdminUserDeactivateView.as_view(),
        name="user-deactivate",
    ),
    path("vendors/", views.AdminVendorListView.as_view(), name="vendor-list"),
    path(
        "vendors/<uuid:id>/",
        views.AdminVendorDetailView.as_view(),
        name="vendor-detail",
    ),
    path(
        "vendors/<uuid:id>/suspend/",
        views.AdminVendorSuspendView.as_view(),
        name="vendor-suspend",
    ),
    path(
        "vendors/<uuid:id>/reinstate/",
        views.AdminVendorReinstateView.as_view(),
        name="vendor-reinstate",
    ),
    path("products/", views.AdminProductListView.as_view(), name="product-list"),
    path(
        "products/<uuid:id>/",
        views.AdminProductDetailView.as_view(),
        name="product-detail",
    ),
    path(
        "products/<uuid:id>/remove/",
        views.AdminProductRemoveView.as_view(),
        name="product-remove",
    ),
    path(
        "categories/",
        views.AdminCategoryListCreateView.as_view(),
        name="category-list-create",
    ),
    path(
        "categories/<slug:slug>/",
        views.AdminCategoryDetailView.as_view(),
        name="category-detail",
    ),
    path(
        "categories/<slug:slug>/activate/",
        views.AdminCategoryActivateView.as_view(),
        name="category-activate",
    ),
    path(
        "categories/<slug:slug>/deactivate/",
        views.AdminCategoryDeactivateView.as_view(),
        name="category-deactivate",
    ),
    path("reports/", views.AdminReportListView.as_view(), name="report-list"),
    path(
        "reports/<uuid:id>/",
        views.AdminReportDetailView.as_view(),
        name="report-detail",
    ),
    path(
        "reports/<uuid:id>/under-review/",
        views.AdminReportUnderReviewView.as_view(),
        name="report-under-review",
    ),
    path(
        "reports/<uuid:id>/resolve/",
        views.AdminReportResolveView.as_view(),
        name="report-resolve",
    ),
    path(
        "reports/<uuid:id>/reject/",
        views.AdminReportRejectView.as_view(),
        name="report-reject",
    ),
]
