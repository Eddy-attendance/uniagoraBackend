class SoftDeleteAdminMixin:
    """
    Standardizes soft-delete-aware columns across every domain app's
    `ModelAdmin`. No `get_queryset` override is needed: `BaseModel.objects`
    is unfiltered by default (see managers.py), so Django admin's default
    queryset already includes soft-deleted rows out of the box, with
    `is_deleted` available as a list column/filter to distinguish them.

    Usage:
        @admin.register(Product)
        class ProductAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
            list_display = (*SoftDeleteAdminMixin.list_display, "name", "status")
    """

    list_display = ("is_deleted", "created_at", "updated_at")
    list_filter = ("is_deleted",)
    readonly_fields = ("id", "created_at", "updated_at")
