from django.contrib import admin

from apps.common.admin import SoftDeleteAdminMixin

from .models import Report


@admin.register(Report)
class ReportAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("id", "target_label", "reason", "status", "reporter", "created_at")
    list_filter = ("status", "reason")
    search_fields = ("reporter__email", "description", "resolution_notes")
    readonly_fields = (
        "reporter",
        "product",
        "vendor_profile",
        "created_at",
        "updated_at",
    )
