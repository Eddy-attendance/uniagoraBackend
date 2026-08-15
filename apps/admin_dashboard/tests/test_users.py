import uuid
from unittest.mock import patch

from rest_framework import status

from .base import AdminAPITestCase


class AdminUserViewTests(AdminAPITestCase):
    def test_list_requires_admin(self):
        self.client.force_authenticate(self.customer)
        r = self.client.get("/api/v1/admin/users/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_rejected(self):
        r = self.client.get("/api/v1/admin/users/")
        self.assertIn(r.status_code, (401, 403))

    def test_admin_lists_users(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get("/api/v1/admin/users/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.json()["success"])

    def test_admin_retrieves_user(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get(f"/api/v1/admin/users/{self.customer.id}/")
        self.assertEqual(r.json()["data"]["email"], self.customer.email)

    def test_unknown_user_404(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get(f"/api/v1/admin/users/{uuid.uuid4()}/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_admin_cannot_deactivate(self):
        self.client.force_authenticate(self.customer)
        r = self.client.post(f"/api/v1/admin/users/{self.admin.id}/deactivate/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_admin_cannot_activate(self):
        self.client.force_authenticate(self.customer)
        r = self.client.post(f"/api/v1/admin/users/{self.admin.id}/activate/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_activate(self):
        r = self.client.post(f"/api/v1/admin/users/{self.customer.id}/activate/")
        self.assertIn(r.status_code, (401, 403))

    def test_is_active_field_is_not_client_writable_via_patch(self):
        self.client.force_authenticate(self.admin)
        r = self.client.patch(
            f"/api/v1/admin/users/{self.customer.id}/", {"is_active": False}
        )
        self.assertEqual(r.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class AdminUserDelegationTests(AdminAPITestCase):
    def test_activate_delegates_to_users_domain_service_exactly_once(self):
        self.client.force_authenticate(self.admin)
        with patch(
            "apps.admin_dashboard.services.UserService.activate"
        ) as mock_activate:
            mock_activate.return_value = self.customer
            r = self.client.post(f"/api/v1/admin/users/{self.customer.id}/activate/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        mock_activate.assert_called_once_with(user=self.customer)

    def test_deactivate_delegates_to_users_domain_service_exactly_once(self):
        self.client.force_authenticate(self.admin)
        with patch(
            "apps.admin_dashboard.services.UserService.deactivate"
        ) as mock_deactivate:
            mock_deactivate.return_value = self.customer
            r = self.client.post(f"/api/v1/admin/users/{self.customer.id}/deactivate/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        mock_deactivate.assert_called_once_with(user=self.customer)

    def test_admin_user_service_has_no_direct_save_call(self):
        import inspect

        from apps.admin_dashboard.services import AdminUserService

        for name in ("activate", "deactivate"):
            source = inspect.getsource(getattr(AdminUserService, name))
            self.assertNotIn(".save(", source)
            self.assertNotIn("is_active =", source)

    def test_conflict_raised_by_users_domain_service_propagates_as_409(self):
        from apps.common.exceptions import ConflictError

        self.client.force_authenticate(self.admin)
        with patch(
            "apps.admin_dashboard.services.UserService.deactivate"
        ) as mock_deactivate:
            mock_deactivate.side_effect = ConflictError("User is already inactive.")
            r = self.client.post(f"/api/v1/admin/users/{self.customer.id}/deactivate/")
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

    def test_activate_deactivate_round_trip_against_real_users_service(self):
        self.client.force_authenticate(self.admin)
        url = f"/api/v1/admin/users/{self.customer.id}/deactivate/"
        r = self.client.post(url)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.json()["data"]["is_active"])

        r = self.client.post(url)  # already inactive
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

        r = self.client.post(f"/api/v1/admin/users/{self.customer.id}/activate/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.json()["data"]["is_active"])
