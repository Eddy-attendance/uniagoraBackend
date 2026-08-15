from rest_framework.routers import SimpleRouter

from apps.chat.views import ConversationViewSet

router = SimpleRouter()
router.register("", ConversationViewSet, basename="conversation")

urlpatterns = router.urls
