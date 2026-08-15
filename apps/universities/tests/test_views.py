from rest_framework import status
from rest_framework.test import APITestCase

from apps.universities.models import University
from apps.users.models import User


def make_user(is_staff=False, is_superuser=False, **kwargs):
    counter = getattr(make_user, "_counter", 0) + 1
    make_user._counter = counter

    email = kwargs.pop("email", f"test-{counter}@example.com")

    return User.objects.create_user(
        email=email,
        password="testpass123",
        is_staff=is_staff,
        is_superuser=is_superuser,
        **kwargs,
    )


class UniversityListViewTests(APITestCase):
    def setUp(self):
        self.active_uni = University.objects.create(name="Active Uni", short_name="ACT")
        self.inactive_uni = University.objects.create(
            name="Inactive Uni", short_name="INA", is_active=False
        )
        self.url = "/api/v1/universities/"

    def test_anonymous_user_is_denied(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data["success"])

    def test_authenticated_customer_sees_only_active_universities(self):
        self.client.force_authenticate(make_user())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        names = [item["short_name"] for item in response.data["data"]["results"]]
        self.assertIn("ACT", names)
        self.assertNotIn("INA", names)

    def test_response_envelope_shape(self):
        self.client.force_authenticate(make_user())
        response = self.client.get(self.url)
        data = response.data["data"]
        keys = (
            "count",
            "total_pages",
            "current_page",
            "page_size",
            "next",
            "previous",
            "results",
        )
        for key in keys:
            self.assertIn(key, data)


class UniversityRetrieveViewTests(APITestCase):
    def setUp(self):
        self.university = University.objects.create(
            name="Retrieve Uni", short_name="RET"
        )
        self.inactive = University.objects.create(
            name="Hidden Uni", short_name="HID", is_active=False
        )

    def test_retrieve_active_university_by_slug(self):
        self.client.force_authenticate(make_user())
        response = self.client.get(f"/api/v1/universities/{self.university.slug}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["short_name"], "RET")

    def test_retrieve_inactive_university_returns_404_for_customer(self):
        self.client.force_authenticate(make_user())
        response = self.client.get(f"/api/v1/universities/{self.inactive.slug}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data["success"])

    def test_retrieve_unknown_slug_returns_404(self):
        self.client.force_authenticate(make_user())
        response = self.client.get("/api/v1/universities/does-not-exist/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class UniversityCreateViewTests(APITestCase):
    def setUp(self):
        self.url = "/api/v1/universities/"

    def test_customer_cannot_create(self):
        self.client.force_authenticate(make_user())
        response = self.client.post(self.url, {"name": "New Uni", "short_name": "NEW"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_create(self):
        response = self.client.post(self.url, {"name": "New Uni", "short_name": "NEW"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_create(self):
        self.client.force_authenticate(make_user(is_staff=True))
        response = self.client.post(self.url, {"name": "New Uni", "short_name": "NEW"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["slug"], "new-uni")
        self.assertTrue(response.data["data"]["is_active"])

    def test_admin_create_rejects_duplicate_name(self):
        University.objects.create(name="Existing", short_name="EX")
        self.client.force_authenticate(make_user(is_staff=True))
        response = self.client.post(
            self.url, {"name": "Existing", "short_name": "NEW2"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_admin_create_cannot_set_is_active_directly(self):
        self.client.force_authenticate(make_user(is_staff=True))
        response = self.client.post(
            self.url, {"name": "Sneaky Uni", "short_name": "SNK", "is_active": False}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["data"]["is_active"])


class UniversityUpdateViewTests(APITestCase):
    def setUp(self):
        self.university = University.objects.create(name="Update Me", short_name="UM")
        self.url = f"/api/v1/universities/{self.university.slug}/"

    def test_customer_cannot_update(self):
        self.client.force_authenticate(make_user())
        response = self.client.patch(self.url, {"name": "Hacked"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_partially_update(self):
        self.client.force_authenticate(make_user(is_staff=True))
        response = self.client.patch(self.url, {"short_name": "UM2"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["short_name"], "UM2")
        self.assertEqual(response.data["data"]["name"], "Update Me")

    def test_admin_update_preserves_slug(self):
        self.client.force_authenticate(make_user(is_staff=True))
        original_slug = self.university.slug
        response = self.client.patch(self.url, {"name": "Update Me Renamed"})
        self.assertEqual(response.data["data"]["slug"], original_slug)

    def test_admin_can_explicitly_clear_logo(self):
        self.university.logo = "https://example.com/existing.png"
        self.university.save(update_fields=["logo"])
        self.client.force_authenticate(make_user(is_staff=True))

        response = self.client.patch(self.url, {"logo": None}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["data"]["logo"])
        self.university.refresh_from_db()
        self.assertIsNone(self.university.logo)

    def test_admin_omitting_logo_in_patch_leaves_existing_logo_untouched(self):
        self.university.logo = "existing-university-logo"
        self.university.save(update_fields=["logo"])

        self.client.force_authenticate(make_user(is_staff=True))

        # Establish the API representation of the existing logo.
        before = self.client.get(self.url)
        self.assertEqual(before.status_code, status.HTTP_200_OK)
        original_logo = before.data["data"]["logo"]

        # PATCH without "logo".
        response = self.client.patch(
            self.url,
            {"short_name": "UM3"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["logo"], original_logo)

        # Verify the logo was not changed in the database.
        after = self.client.get(self.url)
        self.assertEqual(after.status_code, status.HTTP_200_OK)
        self.assertEqual(after.data["data"]["logo"], original_logo)


class UniversityActivationViewTests(APITestCase):
    def setUp(self):
        self.university = University.objects.create(name="Toggle Uni", short_name="TOG")
        self.activate_url = f"/api/v1/universities/{self.university.slug}/activate/"
        self.deactivate_url = f"/api/v1/universities/{self.university.slug}/deactivate/"

    def test_customer_cannot_deactivate(self):
        self.client.force_authenticate(make_user())
        response = self.client.post(self.deactivate_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_deactivate(self):
        self.client.force_authenticate(make_user(is_staff=True))
        response = self.client.post(self.deactivate_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["data"]["is_active"])

    def test_admin_deactivate_twice_returns_409(self):
        self.client.force_authenticate(make_user(is_staff=True))
        self.client.post(self.deactivate_url)
        response = self.client.post(self.deactivate_url)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(response.data["success"])

    def test_admin_can_reactivate(self):
        self.client.force_authenticate(make_user(is_staff=True))
        self.client.post(self.deactivate_url)
        response = self.client.post(self.activate_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["data"]["is_active"])

    def test_admin_deactivate_then_university_hidden_from_customer_list(self):
        self.client.force_authenticate(make_user(is_staff=True))
        self.client.post(self.deactivate_url)

        self.client.force_authenticate(make_user())
        response = self.client.get("/api/v1/universities/")
        short_names = [item["short_name"] for item in response.data["data"]["results"]]
        self.assertNotIn("TOG", short_names)

    def test_superuser_can_activate(self):
        self.university.is_active = False
        self.university.save(update_fields=["is_active"])
        self.client.force_authenticate(make_user(is_superuser=True))
        response = self.client.post(self.activate_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
