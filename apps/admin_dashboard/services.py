from apps.categories.models import Category
from apps.categories.services import CategoryService
from apps.common.exceptions import NotFoundError
from apps.products.models import Product, ProductStatus
from apps.products.services.lifecycle_service import ProductLifecycleService
from apps.reports.models import Report, ReportStatus
from apps.reports.services import ReportService
from apps.users.models import User
from apps.users.services import UserService
from apps.vendors.models import VendorProfile, VendorStatus
from apps.vendors.services import VendorSuspensionService


class DashboardService:
    @staticmethod
    def get_summary() -> dict:
        return {
            "users": {
                "total": User.objects.alive().count(),
                "active": User.objects.alive().filter(is_active=True).count(),
                "inactive": User.objects.alive().filter(is_active=False).count(),
            },
            "vendors": {
                "total": VendorProfile.objects.alive().count(),
                "pending": VendorProfile.objects.alive()
                .filter(status=VendorStatus.PENDING)
                .count(),
                "verified": VendorProfile.objects.alive()
                .filter(status=VendorStatus.VERIFIED)
                .count(),
                "suspended": VendorProfile.objects.alive()
                .filter(status=VendorStatus.SUSPENDED)
                .count(),
                "rejected": VendorProfile.objects.alive()
                .filter(status=VendorStatus.REJECTED)
                .count(),
            },
            "products": {
                "total": Product.objects.alive().count(),
                "active": Product.objects.alive()
                .filter(status=ProductStatus.ACTIVE)
                .count(),
                "expired": Product.objects.alive()
                .filter(status=ProductStatus.EXPIRED)
                .count(),
                "hidden_by_suspension": Product.objects.alive()
                .filter(status=ProductStatus.HIDDEN_BY_SUSPENSION)
                .count(),
                "removed_by_admin": Product.objects.alive()
                .filter(status=ProductStatus.REMOVED_BY_ADMIN)
                .count(),
            },
            "categories": {
                "total": Category.objects.alive().count(),
                "active": Category.objects.alive().filter(is_active=True).count(),
            },
            "reports": {
                "total": Report.objects.alive().count(),
                "pending": Report.objects.alive()
                .filter(status=ReportStatus.PENDING)
                .count(),
                "under_review": Report.objects.alive()
                .filter(status=ReportStatus.UNDER_REVIEW)
                .count(),
                "resolved": Report.objects.alive()
                .filter(status=ReportStatus.RESOLVED)
                .count(),
                "rejected": Report.objects.alive()
                .filter(status=ReportStatus.REJECTED)
                .count(),
            },
        }


class AdminUserService:
    @staticmethod
    def get_queryset():
        return User.objects.alive().select_related("active_university")

    @staticmethod
    def get(*, user_id):
        try:
            return (
                User.objects.alive().select_related("active_university").get(id=user_id)
            )
        except User.DoesNotExist as exc:
            raise NotFoundError("User not found.") from exc

    @staticmethod
    def activate(*, user):
        return UserService.activate(user=user)

    @staticmethod
    def deactivate(*, user):
        return UserService.deactivate(user=user)


class AdminVendorService:
    @staticmethod
    def get_queryset():
        return VendorProfile.objects.alive()

    @staticmethod
    def get(*, vendor_id):
        try:
            return VendorProfile.objects.alive().get(id=vendor_id)
        except VendorProfile.DoesNotExist as exc:
            raise NotFoundError("Vendor not found.") from exc

    @staticmethod
    def suspend(*, vendor_profile):
        return VendorSuspensionService.suspend(vendor_profile=vendor_profile)

    @staticmethod
    def reinstate(*, vendor_profile):
        return VendorSuspensionService.reinstate(vendor_profile=vendor_profile)


class AdminProductService:
    @staticmethod
    def get_queryset():
        return Product.objects.alive()

    @staticmethod
    def get(*, product_id):
        try:
            return Product.objects.alive().get(id=product_id)
        except Product.DoesNotExist as exc:
            raise NotFoundError("Product not found.") from exc

    @staticmethod
    def remove(*, product):
        return ProductLifecycleService.admin_remove(product)


class AdminCategoryService:
    @staticmethod
    def get_queryset(*, parent=None):
        qs = Category.objects.alive()
        if parent is None:
            return qs
        if parent == "null":
            return qs.filter(parent__isnull=True)
        return qs.filter(parent__slug=parent)

    @staticmethod
    def get(*, slug):
        try:
            return Category.objects.alive().get(slug=slug)
        except Category.DoesNotExist as exc:
            raise NotFoundError("Category not found.") from exc

    @staticmethod
    def create(*, name, parent=None, display_order=0):
        parent_obj = AdminCategoryService.get(slug=parent) if parent else None
        return CategoryService.create(
            name=name, parent=parent_obj, display_order=display_order
        )

    @staticmethod
    def update(*, category, name):
        return CategoryService.update(category=category, name=name)

    @staticmethod
    def delete(*, category):
        return CategoryService.delete(category=category)

    @staticmethod
    def activate(*, category):
        return CategoryService.activate(category=category)

    @staticmethod
    def deactivate(*, category):
        return CategoryService.deactivate(category=category)


class AdminReportService:
    @staticmethod
    def get_queryset(*, status=None):
        qs = Report.objects.alive()
        return qs.filter(status=status) if status else qs

    @staticmethod
    def get(*, report_id):
        try:
            return Report.objects.alive().get(id=report_id)
        except Report.DoesNotExist as exc:
            raise NotFoundError("Report not found.") from exc

    @staticmethod
    def mark_under_review(*, report):
        return ReportService.mark_under_review(report)

    @staticmethod
    def resolve(*, report, admin_user, resolution_notes=None):
        return ReportService.resolve(
            report, resolved_by=admin_user, resolution_notes=resolution_notes
        )

    @staticmethod
    def reject(*, report, admin_user, resolution_notes=None):
        return ReportService.reject(
            report, resolved_by=admin_user, resolution_notes=resolution_notes
        )
