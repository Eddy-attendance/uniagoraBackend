from rest_framework.permissions import BasePermission


class IsConversationParticipant(BasePermission):
    message = "You are not a participant in this conversation."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if obj.customer_id == user.id:
            return True
        vendor_user_id = getattr(obj.vendor, "user_id", None)
        return vendor_user_id == user.id
