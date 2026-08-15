from rest_framework import status
from rest_framework.test import APITestCase

from apps.categories.models import Category
from apps.users.models import User


class CategoryViewSetTests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            email="customer@example.com", password="StrongPass123", full_name="Cust"
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="StrongPass123",
            full_name="Admin",
            is_staff=True,
        )
        self.root = Category.objects.create(name="Electronics")
        self.child = Category.objects.create(name="Phones", parent=self.root)
        self.inactive = Category.objects.create(name="Fashion", is_active=False)

    def test_anonymous_list_denied(self):
        response = self.client.get("/api/v1/categories/")
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_customer_list_only_active_alive(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get("/api/v1/categories/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slugs = [item["slug"] for item in response.data["data"]["results"]]
        self.assertIn(self.root.slug, slugs)
        self.assertNotIn(self.inactive.slug, slugs)

    def test_parent_filter(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(f"/api/v1/categories/?parent={self.root.slug}")
        slugs = [item["slug"] for item in response.data["data"]["results"]]
        self.assertEqual(slugs, [self.child.slug])

    def test_retrieve_inactive_returns_404_for_customer(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(f"/api/v1/categories/{self.inactive.slug}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_denied_for_customer(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post("/api/v1/categories/", {"name": "Books"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_allowed_for_admin(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post("/api/v1/categories/", {"name": "Books"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_destroy_blocked_when_active_children_exist(self):
        self.client.force_authenticate(self.admin)
        response = self.client.delete(f"/api/v1/categories/{self.root.slug}/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_destroy_still_blocked_after_deactivating_child(self):
        self.client.force_authenticate(self.admin)

        self.client.post(f"/api/v1/categories/{self.child.slug}/deactivate/")
        response = self.client.delete(f"/api/v1/categories/{self.root.slug}/")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_activate_conflict_propagates_as_409(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(f"/api/v1/categories/{self.root.slug}/activate/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
