"""
apps/chat/permissions.py

Chat needs one object-level permission that `core` cannot provide: is the
requesting user a participant (customer or vendor) of a specific
Conversation? `core.IsOwnerVendor` only resolves ownership for the object
shapes it was built against (`Store`, `Product` — per its own EDD §9,
assumption 3) and does not know about `Conversation`, since `chat` did not
exist yet when `core` was implemented and approved.

Rather than modifying the frozen, already-approved `core` app, this
narrow, chat-specific check is implemented locally — the same
"compose, don't reimplement per view, but do implement what a lower layer
genuinely cannot express" philosophy Architecture §8 already establishes
for every permission class in this codebase.

Baseline authentication continues to use `core.permissions
.IsAuthenticatedCustomer`, composed alongside this class exactly as
Architecture §8 prescribes — this file adds only what `core` cannot.
"""

from rest_framework.permissions import BasePermission


class IsConversationParticipant(BasePermission):
    """
    Object-level only. True if `request.user` is the conversation's
    customer, or the user account behind the conversation's vendor
    profile. Never trusts any client-supplied identifier — the
    comparison is always against the object's own resolved relations,
    mirroring `core.IsOwnerVendor`'s own "never trust a vendor/store ID
    from the request body" rule (Architecture §8).
    """

    message = "You are not a participant in this conversation."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if obj.customer_id == user.id:
            return True
        vendor_user_id = getattr(obj.vendor, "user_id", None)
        return vendor_user_id == user.id
