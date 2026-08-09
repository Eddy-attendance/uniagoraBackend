"""
apps/products/admin.py

Django admin registration, mirroring the `SoftDeleteAdminMixin` convention
already established by every prior app.
"""

from django.contrib import admin

from apps.common.admin import SoftDeleteAdminMixin

from .models import Product, ProductCategory, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ("image", "is_primary", "display_order", "is_deleted")


class ProductCategoryInline(admin.TabularInline):
    model = ProductCategory
    extra = 0
    fields = ("category", "is_deleted")
    autocomplete_fields = ("category",)


@admin.register(Product)
class ProductAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "store",
        "university",
        "status",
        "condition",
        "price",
        "quantity",
        "listed_at",
        "expires_at",
        "is_deleted",
    )
    list_filter = ("status", "condition", "university", "is_deleted")
    search_fields = ("name", "slug", "store__display_name")
    readonly_fields = ("slug", "listed_at", "views_count", "search_vector")
    inlines = [ProductImageInline, ProductCategoryInline]


@admin.register(ProductImage)
class ProductImageAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("product", "is_primary", "display_order", "is_deleted")
    list_filter = ("is_primary", "is_deleted")


@admin.register(ProductCategory)
class ProductCategoryAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("product", "category", "is_deleted")
    list_filter = ("is_deleted",)
