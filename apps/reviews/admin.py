from django.contrib import admin

from apps.common.admin import SoftDeleteAdminMixin

from .models import Review


@admin.register(Review)
class ReviewAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    """
    Inspection-only. `rating`/`comment`/`edited_at` are read-only here
    on purpose
    """

    list_display = ("id", "store", "rating", "is_edited", "created_at", "is_deleted")
    list_filter = ("rating", "is_deleted")
    search_fields = ("store__display_name", "conversation__id")
    autocomplete_fields = ("store", "conversation")
    readonly_fields = (
        "conversation",
        "store",
        "rating",
        "comment",
        "edited_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        # Creation must go through ReviewService (eligibility/ownership
        # checks); no admin-originated review creation path exists.
        return False
