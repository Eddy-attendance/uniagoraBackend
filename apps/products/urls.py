"""
apps/products/urls.py

Uses `SimpleRouter`, not `DefaultRouter` — the same fix already applied to
`stores` post-approval: `mine` is registered solely as a
`@action(detail=False)` on `ProductViewSet`, relying on `SimpleRouter`'s
guaranteed route ordering so `/products/mine/` always matches before
`/products/{slug}/` (see project memory: the `stores` app's
`StoreViewSet`/`/stores/me/` correction). Applying the same router choice here
from the start avoids repeating that class of bug.
"""

from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    ProductImageDetailView,
    ProductImageListCreateView,
    ProductImageSetPrimaryView,
    ProductViewSet,
)

router = SimpleRouter()
router.register("products", ProductViewSet, basename="product")

urlpatterns = router.urls + [
    path(
        "products/<slug:slug>/images/",
        ProductImageListCreateView.as_view(),
        name="product-images",
    ),
    path(
        "products/<slug:slug>/images/<uuid:image_id>/",
        ProductImageDetailView.as_view(),
        name="product-image-detail",
    ),
    path(
        "products/<slug:slug>/images/<uuid:image_id>/primary/",
        ProductImageSetPrimaryView.as_view(),
        name="product-image-primary",
    ),
]
