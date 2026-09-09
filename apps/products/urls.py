from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    ProductImageDetailView,
    ProductImageListCreateView,
    ProductImageSetPrimaryView,
    ProductViewSet,
)

router = SimpleRouter()
router.register("", ProductViewSet, basename="product")

urlpatterns = router.urls + [
    path(
        "<slug:slug>/images/",
        ProductImageListCreateView.as_view(),
        name="product-images",
    ),
    path(
        "<slug:slug>/images/<uuid:image_id>/",
        ProductImageDetailView.as_view(),
        name="product-image-detail",
    ),
    path(
        "<slug:slug>/images/<uuid:image_id>/primary/",
        ProductImageSetPrimaryView.as_view(),
        name="product-image-primary",
    ),
]
