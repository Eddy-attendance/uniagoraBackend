from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.products.models import (
    Product,
    ProductCategory,
    ProductCondition,
    ProductImage,
    ProductStatus,
)

from .factories import (
    make_category,
    make_product,
    make_university,
    make_verified_vendor,
)


class ProductModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.university = make_university()
        _, cls.vendor_profile, cls.store = make_verified_vendor(cls.university)

    def test_str_returns_name(self):
        product = make_product(
            self.store,
            self.university,
            name="Used Textbook",
        )
        self.assertEqual(str(product), "Used Textbook")

    def test_slug_auto_generated_from_name(self):
        product = make_product(
            self.store,
            self.university,
            name="Wireless Mouse",
        )
        self.assertTrue(product.slug)
        self.assertIn("wireless-mouse", product.slug)

    def test_slug_deduplicated_on_collision(self):
        first = make_product(
            self.store,
            self.university,
            name="Same Name",
        )
        second = make_product(
            self.store,
            self.university,
            name="Same Name",
        )
        self.assertNotEqual(first.slug, second.slug)

    def test_slug_not_regenerated_on_rename(self):
        product = make_product(
            self.store,
            self.university,
            name="Original Name",
        )
        original_slug = product.slug

        product.name = "Renamed Product"
        product.save()

        self.assertEqual(product.slug, original_slug)

    def test_expires_at_defaults_to_30_days_from_creation(self):
        product = make_product(
            self.store,
            self.university,
        )
        delta = product.expires_at - product.listed_at

        self.assertAlmostEqual(
            delta.total_seconds(),
            Product.EXPIRY_DAYS * 24 * 60 * 60,
            delta=2,
        )

    def test_status_defaults_to_active(self):
        product = make_product(
            self.store,
            self.university,
        )

        self.assertEqual(
            product.status,
            ProductStatus.ACTIVE,
        )

    def test_price_negative_rejected_by_db_constraint(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_product(
                    self.store,
                    self.university,
                    price=Decimal("-1.00"),
                )

    def test_quantity_negative_rejected_by_db_constraint(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_product(
                    self.store,
                    self.university,
                    quantity=-1,
                )

    def test_is_out_of_stock_true_when_quantity_zero(self):
        product = make_product(
            self.store,
            self.university,
            quantity=0,
        )

        self.assertTrue(product.is_out_of_stock)

    def test_is_out_of_stock_false_when_quantity_positive(self):
        product = make_product(
            self.store,
            self.university,
            quantity=3,
        )

        self.assertFalse(product.is_out_of_stock)

    def test_active_product_with_zero_quantity_keeps_active_status(self):
        """DDS §5 — status and availability are independent axes."""
        product = make_product(
            self.store,
            self.university,
            quantity=0,
        )

        self.assertEqual(
            product.status,
            ProductStatus.ACTIVE,
        )
        self.assertTrue(product.is_out_of_stock)

    def test_primary_image_returns_none_when_no_images(self):
        product = make_product(
            self.store,
            self.university,
        )

        self.assertIsNone(product.primary_image)

    def test_primary_image_returns_the_flagged_image(self):
        product = make_product(
            self.store,
            self.university,
        )

        ProductImage.objects.create(
            product=product,
            image="img1.jpg",
            is_primary=False,
            display_order=1,
        )

        primary = ProductImage.objects.create(
            product=product,
            image="img2.jpg",
            is_primary=True,
            display_order=0,
        )

        self.assertEqual(
            product.primary_image,
            primary,
        )

    def test_soft_delete_regression_unfiltered_manager(self):
        """Mirrors common EDD ADR-001's own regression test intent."""
        product = make_product(
            self.store,
            self.university,
        )

        product.delete()

        self.assertTrue(Product.objects.filter(pk=product.pk).exists())
        self.assertFalse(Product.objects.alive().filter(pk=product.pk).exists())

    def test_condition_choices_are_new_and_used_only(self):
        values = {choice for choice, _ in ProductCondition.choices}

        self.assertEqual(
            values,
            {"NEW", "USED"},
        )

    def test_status_choices_do_not_include_out_of_stock(self):
        values = {choice for choice, _ in ProductStatus.choices}

        self.assertNotIn(
            "OUT_OF_STOCK",
            values,
        )

        self.assertEqual(
            values,
            {
                "ACTIVE",
                "EXPIRED",
                "HIDDEN_BY_SUSPENSION",
                "REMOVED_BY_ADMIN",
            },
        )

    def test_search_vector_populated_on_save(self):
        product = make_product(
            self.store,
            self.university,
            name="Searchable Widget",
            description="A useful university marketplace item",
        )

        product.refresh_from_db()

        self.assertIsNotNone(product.search_vector)

    def test_search_vector_updates_when_name_changes(self):
        product = make_product(
            self.store,
            self.university,
            name="Original Widget",
            description="Original description",
        )

        product.name = "Updated Laptop"
        product.save()
        product.refresh_from_db()

        self.assertIsNotNone(product.search_vector)

    def test_search_vector_updates_when_description_changes(self):
        product = make_product(
            self.store,
            self.university,
            name="Marketplace Item",
            description="Old description",
        )

        product.description = "Engineering textbook"
        product.save()
        product.refresh_from_db()

        self.assertIsNotNone(product.search_vector)


class ProductImageModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.university = make_university()
        _, cls.vendor_profile, cls.store = make_verified_vendor(cls.university)

    def test_image_belongs_to_product(self):
        product = make_product(
            self.store,
            self.university,
        )

        image = ProductImage.objects.create(
            product=product,
            image="a.jpg",
            is_primary=True,
        )

        self.assertEqual(
            image.product,
            product,
        )
        self.assertIn(
            image,
            product.images.all(),
        )

    def test_cascade_delete_from_product_hard_delete(self):
        product = make_product(
            self.store,
            self.university,
        )

        ProductImage.objects.create(
            product=product,
            image="a.jpg",
            is_primary=True,
        )

        product.delete(hard=True)

        self.assertEqual(
            ProductImage.objects.filter(product_id=product.pk).count(),
            0,
        )

    def test_only_one_primary_image_allowed_at_db_level(self):
        product = make_product(
            self.store,
            self.university,
        )

        ProductImage.objects.create(
            product=product,
            image="a.jpg",
            is_primary=True,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductImage.objects.create(
                    product=product,
                    image="b.jpg",
                    is_primary=True,
                )

    def test_different_products_can_each_have_a_primary_image(self):
        product_a = make_product(
            self.store,
            self.university,
            name="Product A",
        )

        product_b = make_product(
            self.store,
            self.university,
            name="Product B",
        )

        ProductImage.objects.create(
            product=product_a,
            image="a.jpg",
            is_primary=True,
        )

        # Must not raise — the partial unique index is scoped per-product.
        ProductImage.objects.create(
            product=product_b,
            image="b.jpg",
            is_primary=True,
        )


class ProductCategoryModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.university = make_university()
        _, cls.vendor_profile, cls.store = make_verified_vendor(cls.university)
        cls.category = make_category()

    def test_duplicate_product_category_pair_rejected(self):
        product = make_product(
            self.store,
            self.university,
        )

        ProductCategory.objects.create(
            product=product,
            category=self.category,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductCategory.objects.create(
                    product=product,
                    category=self.category,
                )

    def test_category_protected_from_deletion_while_referenced(self):
        product = make_product(
            self.store,
            self.university,
        )

        ProductCategory.objects.create(
            product=product,
            category=self.category,
        )

        from django.db.models import ProtectedError

        with self.assertRaises(ProtectedError):
            self.category.delete(hard=True)

    def test_cascade_delete_from_product_hard_delete(self):
        product = make_product(
            self.store,
            self.university,
        )

        ProductCategory.objects.create(
            product=product,
            category=self.category,
        )

        product.delete(hard=True)

        self.assertEqual(
            ProductCategory.objects.filter(product_id=product.pk).count(),
            0,
        )
