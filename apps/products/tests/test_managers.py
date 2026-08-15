from django.test import TestCase

from apps.products.models import Product, ProductStatus

from .factories import make_product, make_university, make_verified_vendor


class ProductManagerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.uni_a = make_university(name="University A", short_name="UA")
        cls.uni_b = make_university(name="University B", short_name="UB")
        _, _, cls.store_a = make_verified_vendor(
            cls.uni_a, email="vendor-a@example.com", store_name="Store A"
        )
        _, _, cls.store_b = make_verified_vendor(
            cls.uni_b, email="vendor-b@example.com", store_name="Store B"
        )

        cls.active_a = make_product(
            cls.store_a, cls.uni_a, name="Active A", status=ProductStatus.ACTIVE
        )
        cls.expired_a = make_product(
            cls.store_a, cls.uni_a, name="Expired A", status=ProductStatus.EXPIRED
        )
        cls.hidden_a = make_product(
            cls.store_a,
            cls.uni_a,
            name="Hidden A",
            status=ProductStatus.HIDDEN_BY_SUSPENSION,
        )
        cls.removed_a = make_product(
            cls.store_a,
            cls.uni_a,
            name="Removed A",
            status=ProductStatus.REMOVED_BY_ADMIN,
        )
        cls.active_b = make_product(
            cls.store_b, cls.uni_b, name="Active B", status=ProductStatus.ACTIVE
        )

        cls.soft_deleted = make_product(
            cls.store_a, cls.uni_a, name="Deleted A", status=ProductStatus.ACTIVE
        )
        cls.soft_deleted.delete()

    def test_objects_unfiltered_by_default(self):
        """ADR-001 regression — mirrors every prior app's own test."""
        self.assertTrue(Product.objects.filter(pk=self.soft_deleted.pk).exists())

    def test_visible_excludes_non_active_statuses(self):
        visible_names = set(Product.objects.visible().values_list("name", flat=True))
        self.assertIn("Active A", visible_names)
        self.assertNotIn("Expired A", visible_names)
        self.assertNotIn("Hidden A", visible_names)
        self.assertNotIn("Removed A", visible_names)

    def test_visible_excludes_soft_deleted(self):
        visible_names = set(Product.objects.visible().values_list("name", flat=True))
        self.assertNotIn("Deleted A", visible_names)

    def test_for_university_filters_by_university(self):
        names = set(
            Product.objects.for_university(self.uni_b).values_list("name", flat=True)
        )
        self.assertEqual(names, {"Active B"})

    def test_visible_composed_with_for_university(self):
        names = set(
            Product.objects.visible()
            .for_university(self.uni_a)
            .values_list("name", flat=True)
        )
        self.assertEqual(names, {"Active A"})
