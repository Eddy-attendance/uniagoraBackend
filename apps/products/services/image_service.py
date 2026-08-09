"""
apps/products/services/image_service.py

Enforces the two DDS-documented image invariants (DDS §4.8/§7.3):
exactly one primary image and a maximum of eight images per product.

"Exactly one primary" has a DB partial-unique-index backstop
(`ProductImage.Meta.constraints`); "max eight" is service-layer only,
per the DDS's explicit note that it is not portably expressible as a
DB constraint.
"""

from django.db import transaction

from apps.common.exceptions import ConflictError, NotFoundError

from ..models import Product, ProductImage

MAX_IMAGES = 8


class ProductImageService:
    @staticmethod
    @transaction.atomic
    def add_image(*, product, image, is_primary=None, display_order=None):
        # Lock the product row so concurrent image mutations for the same
        # product cannot both pass the max-8 check.
        product = Product.objects.select_for_update().get(pk=product.pk)

        existing = product.images.alive()
        count = existing.count()

        if count >= MAX_IMAGES:
            raise ConflictError(f"A product may have at most {MAX_IMAGES} images.")

        make_primary = is_primary if is_primary is not None else (count == 0)

        if make_primary:
            existing.filter(is_primary=True).update(is_primary=False)

        return ProductImage.objects.create(
            product=product,
            image=image,
            is_primary=make_primary,
            display_order=(display_order if display_order is not None else count),
        )

    @staticmethod
    @transaction.atomic
    def set_primary(*, product, image):
        product = Product.objects.select_for_update().get(pk=product.pk)

        if image.product_id != product.id:
            raise NotFoundError("Image not found for this product.")

        product.images.alive().exclude(pk=image.pk).filter(is_primary=True).update(
            is_primary=False
        )

        image.is_primary = True
        image.save(update_fields=["is_primary", "updated_at"])

        return image

    @staticmethod
    @transaction.atomic
    def delete_image(*, product, image):
        product = Product.objects.select_for_update().get(pk=product.pk)

        if image.product_id != product.id:
            raise NotFoundError("Image not found for this product.")

        existing = product.images.alive()

        # A product must retain at least one image, and therefore its
        # primary image, through the normal deletion flow.
        if existing.count() <= 1:
            raise ConflictError(
                "A product must have at least one image; the sole remaining "
                "image cannot be deleted. Add a replacement image first."
            )

        was_primary = image.is_primary

        # Product images have no independent meaning once removed, so they
        # are hard-deleted rather than soft-deleted.
        image.delete(hard=True)

        # If the deleted image was primary, promote the next available image.
        if was_primary:
            next_image = product.images.alive().order_by("display_order", "pk").first()

            if next_image:
                next_image.is_primary = True
                next_image.save(update_fields=["is_primary", "updated_at"])
