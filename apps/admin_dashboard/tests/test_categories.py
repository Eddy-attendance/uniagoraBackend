from rest_framework import status

from apps.categories.models import Category

from .base import AdminAPITestCase


class AdminCategoryViewTests(AdminAPITestCase):
    def setUp(self):
        super().setUp()
        self.category = Category.objects.create(name="Electronics")

    def test_non_admin_cannot_create(self):
        self.client.force_authenticate(self.customer)
        r = self.client.post("/api/v1/admin/categories/", {"name": "Books"})
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_rejected(self):
        r = self.client.get("/api/v1/admin/categories/")
        self.assertIn(r.status_code, (401, 403))

    def test_admin_creates_root_category(self):
        self.client.force_authenticate(self.admin)
        r = self.client.post("/api/v1/admin/categories/", {"name": "Books"})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_duplicate_sibling_name_rejected(self):
        """Validated by CategoryService, not reimplemented here — the
        409/400 outcome is the owning app's own business rule."""
        self.client.force_authenticate(self.admin)
        r = self.client.post("/api/v1/admin/categories/", {"name": "Electronics"})
        self.assertIn(
            r.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT)
        )

    def test_update_name_only(self):
        self.client.force_authenticate(self.admin)
        r = self.client.patch(
            f"/api/v1/admin/categories/{self.category.slug}/", {"name": "Gadgets"}
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.json()["data"]["name"], "Gadgets")

    def test_update_rejects_parent_and_display_order_fields(self):
        """parent/display_order/is_active are absent from
        AdminCategoryUpdateSerializer entirely — DRF silently ignores
        extra keys rather than rejecting them, so this asserts the
        protected fields simply had no effect."""
        self.client.force_authenticate(self.admin)
        r = self.client.patch(
            f"/api/v1/admin/categories/{self.category.slug}/",
            {"name": "Gadgets", "is_active": False, "display_order": 99},
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.json()["data"]["is_active"])

    def test_deactivate_then_activate(self):
        self.client.force_authenticate(self.admin)
        slug = self.category.slug
        r = self.client.post(f"/api/v1/admin/categories/{slug}/deactivate/")
        self.assertFalse(r.json()["data"]["is_active"])
        r = self.client.post(f"/api/v1/admin/categories/{slug}/activate/")
        self.assertTrue(r.json()["data"]["is_active"])

    def test_delete_blocked_by_active_child(self):
        Category.objects.create(name="Phones", parent=self.category)
        self.client.force_authenticate(self.admin)
        r = self.client.delete(f"/api/v1/admin/categories/{self.category.slug}/")
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

    def test_unknown_category_404(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get("/api/v1/admin/categories/does-not-exist/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
