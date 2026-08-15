from unittest.mock import patch

from rest_framework import status

from .base import AdminAPITestCase


class AdminProductViewTests(AdminAPITestCase):
    def test_non_admin_rejected(self):
        self.client.force_authenticate(self.customer)
        r = self.client.get("/api/v1/admin/products/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_rejected(self):
        r = self.client.get("/api/v1/admin/products/")
        self.assertIn(r.status_code, (401, 403))

    def test_admin_lists_products(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get("/api/v1/admin/products/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_status_filter(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get("/api/v1/admin/products/?status=REMOVED_BY_ADMIN")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_unknown_product_404(self):
        import uuid

        self.client.force_authenticate(self.admin)
        r = self.client.get(f"/api/v1/admin/products/{uuid.uuid4()}/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_admin_cannot_remove_product(self):
        import uuid

        self.client.force_authenticate(self.customer)
        r = self.client.post(f"/api/v1/admin/products/{uuid.uuid4()}/remove/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_remove_delegates_to_lifecycle_service_never_sets_status_directly(self):
        """Structural/delegation guard: AdminProductService.remove()
        must call ProductLifecycleService.admin_remove(), never assign
        Product.status itself. Mocked at the admin_dashboard import
        site, consistent with test_users.py/test_vendors.py."""
        import uuid

        fake_product = object()
        with (
            patch("apps.admin_dashboard.services.AdminProductService.get") as mock_get,
            patch(
                "apps.admin_dashboard.services.ProductLifecycleService.admin_remove"
            ) as mock_remove,
        ):
            mock_get.return_value = fake_product
            mock_remove.return_value = fake_product
            self.client.force_authenticate(self.admin)
            self.client.post(f"/api/v1/admin/products/{uuid.uuid4()}/remove/")
        mock_remove.assert_called_once_with(fake_product)

    # test_admin_removes_product_end_to_end (asserts
    # product.status == REMOVED_BY_ADMIN after POST .../remove/ against
    # a real fixture) is intentionally deferred to integration, once the
    # products app's own test-fixture helpers are available in-repo.
