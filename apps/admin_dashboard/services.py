"""
apps/admin_dashboard/services.py

admin_dashboard owns no domain models and performs no direct mutation of
any other app's models. Every method below either:

  (a) runs a read-only aggregate query against another app's own model
      (DashboardService), or
  (b) resolves a target via the owning app's .alive() queryset and then
      delegates the actual mutation to that app's own service.

No business rule (conflict checks, cascade behavior, eligibility,
sibling-uniqueness, verification lifecycle, etc.) is reimplemented
anywhere in this file. This is a hard architectural boundary, not a
soft preference — see the app README for the full rationale.

Revision note (CTO review response): the previous revision of this file
had `AdminUserService.activate()`/`.deactivate()` set `user.is_active`
and call `user.save()` directly, which violated the facade/domain-service
boundary applied consistently to every other model in this app. That has
been corrected — see AdminUserService below. User activation/
deactivation business logic (the no-op/conflict guard, the persistence
call) now lives in `apps.users.services.UserService`, not here.

INTEGRATION NOTE: this session has no repository access. Import paths,
enum names, and exact service method signatures below are inferred from
each app's own EDD, not copied from source. Every inferred spot is
marked "# INTEGRATION POINT" — see docs/INTEGRATION_POINTS.md for the
consolidated list, and docs/USERS_SERVICE_INTEGRATION_PATCH.md for the
one addition this app requires in `apps/users/services.py`.
"""

from apps.categories.models import Category
from apps.categories.services import CategoryService
from apps.common.exceptions import NotFoundError
from apps.products.models import Product, ProductStatus
from apps.products.services.lifecycle_service import ProductLifecycleService
from apps.reports.models import Report, ReportStatus
from apps.reports.services import ReportService

# INTEGRATION POINT — confirm every import path below against the real repo.
from apps.users.models import User
from apps.users.services import UserService
from apps.vendors.models import VendorProfile, VendorStatus
from apps.vendors.services import VendorSuspensionService


class DashboardService:
    """Read-only aggregation across every domain app's own model.

    Each count is the same shape DDS §11 already documents per-app for
    its own admin queue (e.g. "VendorProfile verification queue (admin):
    VendorProfile.objects.filter(status=PENDING)") — this just runs the
    .count() form of that same query for every domain in one call,
    rather than introducing a new read pattern.

    Uses .alive() explicitly (never the unfiltered default) — per common
    EDD §6/ADR-001, aggregation must opt in to exclusion explicitly, and
    a dashboard showing soft-deleted rows as "live" counts would be a
    genuine defect here, not a neutral default.
    """

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
    """Read-side target resolution only. Every mutating action delegates
    to apps.users.services.UserService — admin_dashboard never sets
    User.is_active or calls user.save() directly.

    Flow (per CTO review, enforced here):

        admin_dashboard.AdminUserService
                ↓
        users.services.UserService.activate() / .deactivate()
                ↓
        User.is_active

    Business rules (no-op/conflict guards, no-cascade behavior, the
    actual persistence call) live entirely in UserService — see
    docs/USERS_SERVICE_INTEGRATION_PATCH.md for the exact methods this
    facade depends on. That file must be merged into the real
    apps/users/services.py; it is not part of admin_dashboard itself.
    """

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
        # INTEGRATION POINT — requires UserService.activate() to exist
        # in apps/users/services.py (docs/USERS_SERVICE_INTEGRATION_PATCH.md).
        return UserService.activate(user=user)

    @staticmethod
    def deactivate(*, user):
        # INTEGRATION POINT — requires UserService.deactivate() to exist
        # in apps/users/services.py (docs/USERS_SERVICE_INTEGRATION_PATCH.md).
        return UserService.deactivate(user=user)


class AdminVendorService:
    """Pure delegation to apps.vendors.services.VendorSuspensionService.

    Never mutates VendorProfile.status/Store.is_active directly — every
    call here hits the exact same service apps/vendors/views.py already
    calls at POST /vendors/{id}/suspend/ and /reinstate/ (vendors_EDD
    §5), so both entry points share one code path per Architecture §6's
    Facade description.
    """

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
        # INTEGRATION POINT — confirm exact call signature against real source.
        return VendorSuspensionService.suspend(vendor_profile=vendor_profile)

    @staticmethod
    def reinstate(*, vendor_profile):
        # INTEGRATION POINT — confirm exact call signature against real source.
        return VendorSuspensionService.reinstate(vendor_profile=vendor_profile)


class AdminProductService:
    """Pure delegation to ProductLifecycleService.admin_remove().

    This is the one genuine gap admin_dashboard fills for `products`:
    its own EDD §9 authorizes Admin to "Remove listing" but §5 names no
    endpoint for it, even though the Reports EDD §6.4 confirms
    ProductLifecycleService.admin_remove() already exists (reports calls
    it on report resolution). This gives that same service a directly
    reachable admin entry point, independent of the report workflow.
    Never sets Product.status directly.
    """

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
        # INTEGRATION POINT — confirm admin_remove()'s exact signature
        # (e.g. whether it accepts an acting-admin kwarg) against the
        # real apps/products/services/lifecycle_service.py.
        return ProductLifecycleService.admin_remove(product)


class AdminCategoryService:
    """Pure delegation to apps.categories.services.CategoryService.

    Every method forwards to the identical service apps/categories/
    views.py already calls for its own IsAdmin-gated routes
    (Categories- Edd.md) — sibling-name uniqueness, the delete guard on
    active children, etc. are enforced there, not reimplemented here.
    Never mutates Category rows directly.
    """

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
        # INTEGRATION POINT — confirm CategoryService.create()'s exact kwargs.
        return CategoryService.create(
            name=name, parent=parent_obj, display_order=display_order
        )

    @staticmethod
    def update(*, category, name):
        # INTEGRATION POINT — confirm CategoryService.update()'s exact kwargs.
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
    """Pure delegation to apps.reports.services.ReportService.

    Never mutates Report.status, and never calls into
    ProductLifecycleService/VendorSuspensionService itself — resolution's
    downstream moderation action is entirely ReportService.resolve()'s
    own responsibility (Reports EDD §6.4/§14), not duplicated here.
    """

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
        # INTEGRATION POINT — confirm ReportService.resolve()'s exact
        # kwarg names (resolved_by= vs admin=, etc.) against real source.
        return ReportService.resolve(
            report, resolved_by=admin_user, resolution_notes=resolution_notes
        )

    @staticmethod
    def reject(*, report, admin_user, resolution_notes=None):
        # INTEGRATION POINT — confirm ReportService.reject()'s exact
        # kwarg names against real source.
        return ReportService.reject(
            report, resolved_by=admin_user, resolution_notes=resolution_notes
        )
