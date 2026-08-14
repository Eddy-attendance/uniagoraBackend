from rest_framework import status

from .base import AdminAPITestCase


class DashboardSummaryViewTests(AdminAPITestCase):
    url = "/api/v1/admin/dashboard/"

    def test_unauthenticated_rejected(self):
        self.assertIn(self.client.get(self.url).status_code, (401, 403))

    def test_non_admin_rejected(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN
        )

    def test_admin_gets_summary_envelope(self):
        self.client.force_authenticate(self.admin)
        body = self.client.get(self.url).json()
        self.assertTrue(body["success"])
        for key in ("users", "vendors", "products", "categories", "reports"):
            self.assertIn(key, body["data"])

    def test_empty_platform_returns_zero_domain_counts(self):
        self.client.force_authenticate(self.admin)
        data = self.client.get(self.url).json()["data"]
        self.assertGreaterEqual(data["users"]["total"], 2)  # admin + customer
        self.assertEqual(data["vendors"]["total"], 0)
        self.assertEqual(data["products"]["total"], 0)
        self.assertEqual(data["reports"]["total"], 0)

    def test_response_uses_standard_success_envelope(self):
        self.client.force_authenticate(self.admin)
        body = self.client.get(self.url).json()
        self.assertEqual(set(body.keys()), {"success", "message", "data"})
