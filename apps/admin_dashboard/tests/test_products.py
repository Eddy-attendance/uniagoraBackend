from unittest.mock import patch

from rest_framework import status

from apps.products.models import ProductStatus
from apps.products.tests.factories import (
    make_product,
    make_university,
    make_verified_vendor,
)

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
        mock_remove.assert_called_once_with(product=fake_product)

    # -- Unmocked integration test ---------------------------------------
    #
    # Mocked delegation guards cannot catch signature drift between
    # AdminProductService.remove() and
    # ProductLifecycleService.admin_remove() — a mock accepts any call
    # convention, which is exactly how the positional-call regression
    # against the keyword-only callee shipped. This test exercises the
    # real view -> AdminProductService -> ProductLifecycleService path.

    def test_admin_removes_product_end_to_end(self):
        """Regression guard: POST .../remove/ must succeed against the
        real ProductLifecycleService.

        A wrong call contract between AdminProductService and
        ProductLifecycleService surfaces here as a 500 (TypeError)
        instead of a 200, and the product's status is never transitioned
        (DDS §9.4: admin removal sets REMOVED_BY_ADMIN).
        """
        university = make_university()
        _, _, store = make_verified_vendor(university)
        product = make_product(store, university)

        # Permission boundary: a non-admin must not reach the service.
        self.client.force_authenticate(self.customer)
        forbidden = self.client.post(f"/api/v1/admin/products/{product.id}/remove/")
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.admin)
        response = self.client.post(f"/api/v1/admin/products/{product.id}/remove/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Envelope contract (PRD §17) is preserved.
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["message"], "Product removed.")

        product.refresh_from_db()
        self.assertEqual(product.status, ProductStatus.REMOVED_BY_ADMIN)
