from rest_framework.permissions import BasePermission


class IsReviewOwner(BasePermission):
    """Object-level only. Ownership is derived exclusively from the
    review's own `conversation.customer` relation — never a client-
    supplied identifier, mirroring `core.IsOwnerVendor`'s pattern."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return obj.conversation.customer_id == user.id
