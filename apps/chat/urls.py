"""
apps/chat/urls.py

SimpleRouter, matching the project-wide convention (see the `stores`
EDD's `/stores/me/` note and Backend Architecture's stated preference for
SimpleRouter across all viewset-based apps). Sub-resources (messages,
read, complete) are `@action`s on `ConversationViewSet`, not separate
routers — no `detail=False` route-ordering concern arises here since none
of these actions collides with a lookup-field pattern the way
`/stores/me/` did against `/stores/{slug}/`.
"""

from rest_framework.routers import SimpleRouter

from apps.chat.views import ConversationViewSet

router = SimpleRouter()
router.register("", ConversationViewSet, basename="conversation")

urlpatterns = router.urls
