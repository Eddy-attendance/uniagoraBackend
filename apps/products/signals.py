"""
apps/products/signals.py

Two signal-maintained invariants:

1. Product.search_vector from Product.name and Product.description.

   The stored SearchVectorField is required by the DDS for PostgreSQL full-text
   search. A post_save signal keeps it synchronized without recursively calling
   Product.save().

2. Cloudinary asset cleanup when a ProductImage row is really deleted.

   The Cloudinary SDK field uploads in pre_save but does NOT destroy the
   remote asset on row deletion, so hard deletes (ProductImageService,
   product hard-delete cascade, admin) would otherwise orphan the asset.
   post_delete is the single choke point: it fires exactly once per really
   removed row and never on soft deletes (BaseModel.delete(hard=False) only
   flips is_deleted), so cleanup cannot double-run.
"""

import logging

from cloudinary import uploader
from django.contrib.postgres.search import SearchVector
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Product, ProductImage

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Product)
def update_product_search_vector(sender, instance, **kwargs):
    """
    Synchronize the stored search vector after a Product is saved.

    QuerySet.update() is deliberately used instead of instance.save() to
    prevent recursive signal execution.
    """
    sender.objects.filter(pk=instance.pk).update(
        search_vector=SearchVector(
            "name",
            "description",
            config="english",
        ),
    )


@receiver(post_delete, sender=ProductImage)
def destroy_product_image_asset(sender, instance, **kwargs):
    """Best-effort removal of the Cloudinary asset behind a deleted row.

    Never raises: an asset is garbage once its row is gone, and a transient
    Cloudinary outage must not fail a delete request that already succeeded
    at the database level. Destroying an already-missing public_id returns
    {"result": "not found"}, so retries are harmless too.
    """
    value = instance.image

    if isinstance(value, str):
        # In-memory instances may carry the raw DB string (e.g. a value set
        # without passing through the field). Normalize it the same way
        # from_db_value would so the public_id is available.
        try:
            value = sender._meta.get_field("image").to_python(value)
        except Exception:  # noqa: BLE001 — unparseable value means no asset
            return

    public_id = getattr(value, "public_id", None)

    if not public_id:
        return

    try:
        # Resolved lazily off the uploader module so tests can patch
        # "cloudinary.uploader.destroy" — the same boundary style used for
        # "cloudinary.uploader.upload" elsewhere in the suite.
        uploader.destroy(public_id, invalidate=True)
    except Exception:  # noqa: BLE001 — cleanup must never break deletion
        logger.warning(
            "Cloudinary destroy failed for product image %s (public_id=%s)",
            instance.pk,
            public_id,
            exc_info=True,
        )
