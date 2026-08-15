from django.db import transaction

from apps.categories.models import Category
from apps.common.exceptions import ApplicationError, ConflictError, NotFoundError
from apps.stores.models import Store

from ..models import Product, ProductCategory

UNSET = object()


class ProductService:
    @staticmethod
    @transaction.atomic
    def create(
        *,
        vendor_profile,
        name,
        price,
        condition,
        primary_image=None,
        description="",
        quantity=1,
        campus_location=None,
        category_ids=None,
    ):
        """Create a Product with its required primary image.

        The product and its first image are created within the same
        transaction so a listing can never be persisted without its required
        primary image.

        Ownership and university are derived from the authenticated vendor's
        own Store/VendorProfile relationship. The client cannot provide them.
        """
        if primary_image is None:
            raise ApplicationError(
                "A primary image is required when creating a product.",
                errors={
                    "primary_image": [
                        "A primary image is required when creating a product."
                    ]
                },
            )

        store = _get_owned_store(vendor_profile)

        product = Product.objects.create(
            store=store,
            university=store.vendor_profile.university,
            name=name,
            description=description or "",
            price=price,
            condition=condition,
            quantity=quantity,
            campus_location=campus_location,
        )

        if category_ids:
            ProductService.set_categories(
                product=product,
                category_ids=category_ids,
            )

        from .image_service import ProductImageService

        ProductImageService.add_image(
            product=product,
            image=primary_image,
            is_primary=True,
            display_order=0,
        )
        return product

    @staticmethod
    @transaction.atomic
    def update(
        *,
        product,
        name=UNSET,
        description=UNSET,
        price=UNSET,
        condition=UNSET,
        campus_location=UNSET,
        category_ids=UNSET,
    ):
        if name is not UNSET:
            product.name = name
        if description is not UNSET:
            product.description = description or ""
        if price is not UNSET:
            product.price = price
        if condition is not UNSET:
            product.condition = condition
        if campus_location is not UNSET:
            product.campus_location = campus_location
        product.save()
        if category_ids is not UNSET:
            ProductService.set_categories(product=product, category_ids=category_ids)
        return product

    @staticmethod
    @transaction.atomic
    def set_categories(*, product, category_ids):
        """Replaces the product's full category assignment set."""
        category_ids = list(category_ids or [])
        if len(category_ids) != len(set(category_ids)):
            raise ApplicationError(
                "Duplicate category IDs are not allowed.",
                errors={"category_ids": ["Duplicate category IDs are not allowed."]},
            )
        categories = list(
            Category.objects.alive().filter(is_active=True, id__in=category_ids)
        )
        found_ids = {str(c.id) for c in categories}
        missing = {str(cid) for cid in category_ids} - found_ids
        if missing:
            raise NotFoundError(
                "One or more categories were not found.",
                errors={"category_ids": sorted(missing)},
            )
        ProductCategory.objects.filter(product=product).hard_delete()
        ProductCategory.objects.bulk_create(
            [
                ProductCategory(product=product, category=category)
                for category in categories
            ]
        )
        return product

    @staticmethod
    def delete(*, product):
        """Vendor 'Delete Listing' Soft-delete only"""
        product.delete()


def _get_owned_store(vendor_profile):
    try:
        return vendor_profile.store
    except Store.DoesNotExist:
        raise ConflictError(
            "You must create a store before listing products."
        ) from None
