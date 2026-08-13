from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path(
        "products/<uuid:product_id>/",
        views.ReportProductCreateView.as_view(),
        name="report-product",
    ),
    path(
        "vendors/<uuid:vendor_id>/",
        views.ReportVendorCreateView.as_view(),
        name="report-vendor",
    ),
    path("mine/", views.MyReportsListView.as_view(), name="my-reports"),
    path(
        "<uuid:report_id>/under-review/",
        views.ReportUnderReviewView.as_view(),
        name="report-under-review",
    ),
    path(
        "<uuid:report_id>/resolve/",
        views.ReportResolveView.as_view(),
        name="report-resolve",
    ),
    path(
        "<uuid:report_id>/reject/",
        views.ReportRejectView.as_view(),
        name="report-reject",
    ),
    path("<uuid:report_id>/", views.ReportDetailView.as_view(), name="report-detail"),
    path("", views.ReportAdminListView.as_view(), name="report-admin-list"),
]
