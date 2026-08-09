"""
apps/products/tests/test_services.py

Covers every service listed in the products implementation:
ProductService, InventoryService, ProductLifecycleService, and
ProductImageService.
"""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.common.exceptions import ApplicationError, ConflictError, NotFoundError
from apps.products.models import (
    Product,
    ProductCondition,
    ProductImage,
    ProductStatus,
)
from apps.products.services import (
    InventoryService,
    ProductImageService,
    ProductLifecycleService,
    ProductService,
)

from .factories import (
    make_category,
    make_product,
    make_university,
    make_verified_vendor,
)


class ProductServiceCreateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.university = make_university()
        _, cls.vendor_profile, cls.store = make_verified_vendor(cls.university)
        cls.category = make_category()

    @staticmethod
    def make_primary_image():
        # ProductImageService stores the uploaded file reference.
        # Service-level tests do not need to exercise ImageField validation;
        # serializer tests cover that boundary.
        return "products/test/primary.jpg"

    def test_create_requires_primary_image(self):
        with self.assertRaises(ApplicationError):
            ProductService.create(
                vendor_profile=self.vendor_profile,
                name="New Listing",
                price=Decimal("50.00"),
                condition=ProductCondition.NEW,
            )

    def test_create_persists_product_owned_by_vendors_store(self):
        product = ProductService.create(
            vendor_profile=self.vendor_profile,
            name="New Listing",
            price=Decimal("50.00"),
            condition=ProductCondition.NEW,
            primary_image=self.make_primary_image(),
        )

        self.assertEqual(product.store, self.store)

    def test_create_derives_university_from_store_vendor_profile(self):
        product = ProductService.create(
            vendor_profile=self.vendor_profile,
            name="New Listing",
            price=Decimal("50.00"),
            condition=ProductCondition.NEW,
            primary_image=self.make_primary_image(),
        )

        self.assertEqual(product.university, self.vendor_profile.university)

    def test_create_defaults_status_to_active(self):
        product = ProductService.create(
            vendor_profile=self.vendor_profile,
            name="New Listing",
            price=Decimal("50.00"),
            condition=ProductCondition.NEW,
            primary_image=self.make_primary_image(),
        )

        self.assertEqual(product.status, ProductStatus.ACTIVE)

    def test_create_assigns_categories(self):
        product = ProductService.create(
            vendor_profile=self.vendor_profile,
            name="New Listing",
            price=Decimal("50.00"),
            condition=ProductCondition.NEW,
            primary_image=self.make_primary_image(),
            category_ids=[self.category.id],
        )

        self.assertEqual(
            set(product.category_links.values_list("category_id", flat=True)),
            {self.category.id},
        )

    def test_create_creates_required_primary_image(self):
        product = ProductService.create(
            vendor_profile=self.vendor_profile,
            name="New Listing",
            price=Decimal("50.00"),
            condition=ProductCondition.NEW,
            primary_image=self.make_primary_image(),
        )

        images = product.images.alive()

        self.assertEqual(images.count(), 1)

        image = images.get()

        self.assertTrue(image.is_primary)
        self.assertEqual(image.display_order, 0)
        self.assertEqual(
            image.image.public_id,
            "products/test/primary",
        )
        self.assertEqual(image.image.format, "jpg")

    def test_create_without_store_raises_conflict(self):
        from apps.users.models import User
        from apps.vendors.models import VendorProfile, VendorStatus, VendorType

        user = User.objects.create_user(
            email="storeless@example.com",
            password="Testpass123!",
            full_name="Storeless Vendor",
            active_university=self.university,
        )

        vendor_profile = VendorProfile.objects.create(
            user=user,
            university=self.university,
            vendor_type=VendorType.STUDENT,
            store_name="No Store Yet",
            phone_number="+2348000000000",
            matric_number="MAT/9999",
            department="Physics",
            level="200",
            status=VendorStatus.VERIFIED,
        )

        with self.assertRaises(ConflictError):
            ProductService.create(
                vendor_profile=vendor_profile,
                name="X",
                price=Decimal("1.00"),
                condition=ProductCondition.NEW,
                primary_image=self.make_primary_image(),
            )


class ProductServiceUpdateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.university = make_university()
        _, cls.vendor_profile, cls.store = make_verified_vendor(cls.university)
        cls.category_a = make_category(name="Category A")
        cls.category_b = make_category(name="Category B")

    def test_update_only_touches_provided_fields(self):
        product = make_product(
            self.store,
            self.university,
            name="Original",
            price=Decimal("10.00"),
        )

        ProductService.update(
            product=product,
            price=Decimal("20.00"),
        )

        product.refresh_from_db()

        self.assertEqual(product.name, "Original")
        self.assertEqual(product.price, Decimal("20.00"))

    def test_update_never_touches_quantity(self):
        """Quantity mutation is InventoryService's exclusive responsibility."""
        product = make_product(
            self.store,
            self.university,
            quantity=5,
        )

        ProductService.update(
            product=product,
            name="Renamed",
        )

        product.refresh_from_db()

        self.assertEqual(product.quantity, 5)

    def test_update_replaces_category_assignment(self):
        product = make_product(
            self.store,
            self.university,
        )

        ProductService.set_categories(
            product=product,
            category_ids=[self.category_a.id],
        )

        ProductService.update(
            product=product,
            category_ids=[self.category_b.id],
        )

        self.assertEqual(
            set(product.category_links.values_list("category_id", flat=True)),
            {self.category_b.id},
        )

    def test_set_categories_with_unknown_id_raises_not_found(self):
        import uuid

        product = make_product(
            self.store,
            self.university,
        )

        with self.assertRaises(NotFoundError):
            ProductService.set_categories(
                product=product,
                category_ids=[uuid.uuid4()],
            )

    def test_set_categories_can_be_replaced_after_removal(self):
        """
        Regression: hard-delete on replace avoids the soft-delete /
        UNIQUE(product, category) collision class of bug.
        """
        product = make_product(
            self.store,
            self.university,
        )

        ProductService.set_categories(
            product=product,
            category_ids=[self.category_a.id],
        )

        ProductService.set_categories(
            product=product,
            category_ids=[],
        )

        ProductService.set_categories(
            product=product,
            category_ids=[self.category_a.id],
        )

        self.assertEqual(
            set(product.category_links.values_list("category_id", flat=True)),
            {self.category_a.id},
        )

    def test_delete_soft_deletes_only(self):
        product = make_product(
            self.store,
            self.university,
        )

        ProductService.delete(product=product)

        self.assertTrue(Product.objects.filter(pk=product.pk).exists())
        self.assertFalse(Product.objects.alive().filter(pk=product.pk).exists())


class InventoryServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.university = make_university()
        _, cls.vendor_profile, cls.store = make_verified_vendor(cls.university)

    def test_set_quantity_updates_value(self):
        product = make_product(
            self.store,
            self.university,
            quantity=5,
        )

        InventoryService.set_quantity(
            product=product,
            quantity=10,
        )

        product.refresh_from_db()

        self.assertEqual(product.quantity, 10)

    def test_set_negative_quantity_rejected(self):
        product = make_product(
            self.store,
            self.university,
            quantity=5,
        )

        with self.assertRaises(ApplicationError):
            InventoryService.set_quantity(
                product=product,
                quantity=-1,
            )

    def test_increase_quantity(self):
        product = make_product(
            self.store,
            self.university,
            quantity=5,
        )

        InventoryService.increase_quantity(
            product=product,
            amount=3,
        )

        product.refresh_from_db()

        self.assertEqual(product.quantity, 8)

    def test_decrease_quantity(self):
        product = make_product(
            self.store,
            self.university,
            quantity=5,
        )

        InventoryService.decrease_quantity(
            product=product,
            amount=2,
        )

        product.refresh_from_db()

        self.assertEqual(product.quantity, 3)

    def test_decrease_below_zero_raises_conflict(self):
        product = make_product(
            self.store,
            self.university,
            quantity=2,
        )

        with self.assertRaises(ConflictError):
            InventoryService.decrease_quantity(
                product=product,
                amount=5,
            )

    def test_zero_quantity_marks_out_of_stock(self):
        product = make_product(
            self.store,
            self.university,
            quantity=1,
        )

        InventoryService.decrease_quantity(
            product=product,
            amount=1,
        )

        product.refresh_from_db()

        self.assertTrue(product.is_out_of_stock)

    def test_restoring_quantity_marks_in_stock_again(self):
        product = make_product(
            self.store,
            self.university,
            quantity=0,
        )

        InventoryService.increase_quantity(
            product=product,
            amount=1,
        )

        product.refresh_from_db()

        self.assertFalse(product.is_out_of_stock)

    def test_status_independent_of_quantity_changes(self):
        product = make_product(
            self.store,
            self.university,
            quantity=1,
            status=ProductStatus.ACTIVE,
        )

        InventoryService.decrease_quantity(
            product=product,
            amount=1,
        )

        product.refresh_from_db()

        self.assertEqual(product.status, ProductStatus.ACTIVE)


class ProductLifecycleServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.university = make_university()
        _, cls.vendor_profile, cls.store = make_verified_vendor(cls.university)

    def test_new_product_is_active(self):
        product = make_product(
            self.store,
            self.university,
        )

        self.assertEqual(
            product.status,
            ProductStatus.ACTIVE,
        )

    def test_sweep_expire_transitions_past_due_active_products(self):
        product = make_product(
            self.store,
            self.university,
            status=ProductStatus.ACTIVE,
        )

        Product.objects.filter(pk=product.pk).update(
            expires_at=timezone.now() - timezone.timedelta(days=1)
        )

        count = ProductLifecycleService.sweep_expire()

        product.refresh_from_db()

        self.assertEqual(count, 1)
        self.assertEqual(
            product.status,
            ProductStatus.EXPIRED,
        )

    def test_sweep_expire_ignores_not_yet_due_products(self):
        product = make_product(
            self.store,
            self.university,
            status=ProductStatus.ACTIVE,
        )

        count = ProductLifecycleService.sweep_expire()

        product.refresh_from_db()

        self.assertEqual(count, 0)
        self.assertEqual(
            product.status,
            ProductStatus.ACTIVE,
        )

    def test_expired_listing_hidden_from_visible_queryset(self):
        product = make_product(
            self.store,
            self.university,
            status=ProductStatus.EXPIRED,
        )

        self.assertNotIn(
            product,
            Product.objects.visible(),
        )

    def test_renew_from_expired_succeeds(self):
        product = make_product(
            self.store,
            self.university,
            status=ProductStatus.EXPIRED,
        )

        ProductLifecycleService.renew(product=product)

        product.refresh_from_db()

        self.assertEqual(
            product.status,
            ProductStatus.ACTIVE,
        )

    def test_renew_resets_expiry(self):
        product = make_product(
            self.store,
            self.university,
            status=ProductStatus.EXPIRED,
        )

        Product.objects.filter(pk=product.pk).update(
            expires_at=timezone.now() - timezone.timedelta(days=5)
        )

        ProductLifecycleService.renew(product=product)

        product.refresh_from_db()

        self.assertGreater(
            product.expires_at,
            timezone.now(),
        )

    def test_renew_rejected_from_active(self):
        product = make_product(
            self.store,
            self.university,
            status=ProductStatus.ACTIVE,
        )

        with self.assertRaises(ConflictError):
            ProductLifecycleService.renew(product=product)

    def test_renew_rejected_from_hidden_by_suspension(self):
        product = make_product(
            self.store,
            self.university,
            status=ProductStatus.HIDDEN_BY_SUSPENSION,
        )

        with self.assertRaises(ConflictError):
            ProductLifecycleService.renew(product=product)

    def test_renew_rejected_from_removed_by_admin(self):
        product = make_product(
            self.store,
            self.university,
            status=ProductStatus.REMOVED_BY_ADMIN,
        )

        with self.assertRaises(ConflictError):
            ProductLifecycleService.renew(product=product)

    def test_suspend_store_products_hides_active_only(self):
        active = make_product(
            self.store,
            self.university,
            name="A",
            status=ProductStatus.ACTIVE,
        )

        expired = make_product(
            self.store,
            self.university,
            name="B",
            status=ProductStatus.EXPIRED,
        )

        ProductLifecycleService.suspend_store_products(
            store=self.store,
        )

        active.refresh_from_db()
        expired.refresh_from_db()

        self.assertEqual(
            active.status,
            ProductStatus.HIDDEN_BY_SUSPENSION,
        )
        self.assertEqual(
            expired.status,
            ProductStatus.EXPIRED,
        )

    def test_reinstate_before_expiry_restores_active(self):
        product = make_product(
            self.store,
            self.university,
            status=ProductStatus.HIDDEN_BY_SUSPENSION,
        )

        ProductLifecycleService.reinstate_store_products(
            store=self.store,
        )

        product.refresh_from_db()

        self.assertEqual(
            product.status,
            ProductStatus.ACTIVE,
        )

    def test_reinstate_after_expiry_becomes_expired(self):
        product = make_product(
            self.store,
            self.university,
            status=ProductStatus.HIDDEN_BY_SUSPENSION,
        )

        Product.objects.filter(pk=product.pk).update(
            expires_at=timezone.now() - timezone.timedelta(days=1)
        )

        ProductLifecycleService.reinstate_store_products(
            store=self.store,
        )

        product.refresh_from_db()

        self.assertEqual(
            product.status,
            ProductStatus.EXPIRED,
        )

    def test_admin_removal_from_active(self):
        product = make_product(
            self.store,
            self.university,
            status=ProductStatus.ACTIVE,
        )

        ProductLifecycleService.admin_remove(
            product=product,
        )

        product.refresh_from_db()

        self.assertEqual(
            product.status,
            ProductStatus.REMOVED_BY_ADMIN,
        )

    def test_admin_removal_is_terminal(self):
        product = make_product(
            self.store,
            self.university,
            status=ProductStatus.REMOVED_BY_ADMIN,
        )

        with self.assertRaises(ConflictError):
            ProductLifecycleService.admin_remove(
                product=product,
            )


class ProductImageServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.university = make_university()
        _, cls.vendor_profile, cls.store = make_verified_vendor(cls.university)

    def test_first_image_becomes_primary_automatically(self):
        product = make_product(
            self.store,
            self.university,
        )

        image = ProductImageService.add_image(
            product=product,
            image="a.jpg",
        )

        self.assertTrue(image.is_primary)

    def test_second_image_is_not_primary_by_default(self):
        product = make_product(
            self.store,
            self.university,
        )

        ProductImageService.add_image(
            product=product,
            image="a.jpg",
        )

        second = ProductImageService.add_image(
            product=product,
            image="b.jpg",
        )

        self.assertFalse(second.is_primary)

    def test_explicit_primary_demotes_previous_primary(self):
        product = make_product(
            self.store,
            self.university,
        )

        first = ProductImageService.add_image(
            product=product,
            image="a.jpg",
        )

        second = ProductImageService.add_image(
            product=product,
            image="b.jpg",
            is_primary=True,
        )

        first.refresh_from_db()

        self.assertFalse(first.is_primary)
        self.assertTrue(second.is_primary)

    def test_exactly_one_primary_enforced_across_additions(self):
        product = make_product(
            self.store,
            self.university,
        )

        for i in range(3):
            ProductImageService.add_image(
                product=product,
                image=f"{i}.jpg",
                is_primary=(i == 1),
            )

        self.assertEqual(
            product.images.filter(is_primary=True).count(),
            1,
        )

    def test_max_eight_images_enforced(self):
        product = make_product(
            self.store,
            self.university,
        )

        for i in range(8):
            ProductImageService.add_image(
                product=product,
                image=f"{i}.jpg",
            )

        with self.assertRaises(ConflictError):
            ProductImageService.add_image(
                product=product,
                image="ninth.jpg",
            )

    def test_set_primary_switches_flag(self):
        product = make_product(
            self.store,
            self.university,
        )

        first = ProductImageService.add_image(
            product=product,
            image="a.jpg",
        )

        second = ProductImageService.add_image(
            product=product,
            image="b.jpg",
        )

        ProductImageService.set_primary(
            product=product,
            image=second,
        )

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertFalse(first.is_primary)
        self.assertTrue(second.is_primary)

    def test_set_primary_rejects_image_from_another_product(self):
        product_a = make_product(
            self.store,
            self.university,
            name="A",
        )

        product_b = make_product(
            self.store,
            self.university,
            name="B",
        )

        image_b = ProductImageService.add_image(
            product=product_b,
            image="b.jpg",
        )

        with self.assertRaises(NotFoundError):
            ProductImageService.set_primary(
                product=product_a,
                image=image_b,
            )

    def test_deleting_non_primary_image_leaves_primary_untouched(self):
        product = make_product(
            self.store,
            self.university,
        )

        primary = ProductImageService.add_image(
            product=product,
            image="a.jpg",
        )

        second = ProductImageService.add_image(
            product=product,
            image="b.jpg",
        )

        ProductImageService.delete_image(
            product=product,
            image=second,
        )

        primary.refresh_from_db()

        self.assertTrue(primary.is_primary)

    def test_deleting_primary_image_promotes_next_image(self):
        product = make_product(
            self.store,
            self.university,
        )

        primary = ProductImageService.add_image(
            product=product,
            image="a.jpg",
        )

        second = ProductImageService.add_image(
            product=product,
            image="b.jpg",
        )

        ProductImageService.delete_image(
            product=product,
            image=primary,
        )

        second.refresh_from_db()

        self.assertTrue(second.is_primary)

    def test_deleting_only_image_is_rejected(self):
        product = make_product(
            self.store,
            self.university,
        )

        only = ProductImageService.add_image(
            product=product,
            image="a.jpg",
        )

        with self.assertRaises(ConflictError):
            ProductImageService.delete_image(
                product=product,
                image=only,
            )

        only.refresh_from_db()

        self.assertTrue(only.is_primary)

    def test_delete_image_is_hard_delete(self):
        product = make_product(
            self.store,
            self.university,
        )

        primary = ProductImageService.add_image(
            product=product,
            image="a.jpg",
        )

        second = ProductImageService.add_image(
            product=product,
            image="b.jpg",
        )

        ProductImageService.delete_image(
            product=product,
            image=second,
        )

        self.assertFalse(ProductImage.objects.filter(pk=second.pk).exists())

        primary.refresh_from_db()

        self.assertTrue(primary.is_primary)

    def test_freed_slot_after_deletion_allows_new_image(self):
        product = make_product(
            self.store,
            self.university,
        )

        images = [
            ProductImageService.add_image(
                product=product,
                image=f"{i}.jpg",
            )
            for i in range(8)
        ]

        ProductImageService.delete_image(
            product=product,
            image=images[1],
        )

        ProductImageService.add_image(
            product=product,
            image="new.jpg",
        )

        self.assertEqual(
            product.images.alive().count(),
            8,
        )
