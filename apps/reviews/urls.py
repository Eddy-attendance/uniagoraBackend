from django.urls import path

from .views import (
    ConversationReviewView,
    ReviewDetailView,
    StoreReviewListView,
)

app_name = "reviews"

urlpatterns = [
    path(
        "conversations/<uuid:conversation_id>/",
        ConversationReviewView.as_view(),
        name="conversation-review",
    ),
    path(
        "<uuid:pk>/",
        ReviewDetailView.as_view(),
        name="review-detail",
    ),
    path(
        "stores/<slug:store_slug>/",
        StoreReviewListView.as_view(),
        name="store-review-list",
    ),
]
