"""
`reviews` owns exactly one object-level permission not already covered by
`core`: review-edit ownership. `core.permissions` has no knowledge of
`Review` (a domain model that postdates `core`'s own build-order
position) and never will — new domain permissions belong in the owning
app, not bolted onto the frozen `core` app. This mirrors
`chat.permissions.IsConversationParticipant`'s own precedent exactly.

Conversation-participant checks for review retrieval/creation reuse
`chat.permissions.IsConversationParticipant` directly (DDS §3: `reviews`
depends on `chat`) rather than being reimplemented here.
"""

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
