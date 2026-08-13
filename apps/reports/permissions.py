from rest_framework.permissions import BasePermission


class IsReportOwnerOrAdmin(BasePermission):
    """
    Object-level only (no has_permission override — mirrors
    core.IsOwnerVendor's precedent, core EDD §5.3): grants access to the
    reporter who filed the report, or to staff/admin. Ownership is
    resolved exclusively from the object itself, never from a
    client-supplied identifier.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        return obj.reporter_id == user.id
