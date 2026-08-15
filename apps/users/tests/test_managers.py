from django.test import TestCase

from apps.users.models import User


class UserManagerTests(TestCase):
    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="pass12345", full_name="X")

    def test_create_user_sets_unusable_password_when_none(self):
        user = User.objects.create_user(
            email="k@example.com", password=None, full_name="K"
        )
        self.assertFalse(user.has_usable_password())

    def test_create_superuser_flags(self):
        user = User.objects.create_superuser(
            email="l@example.com", password="pass12345", full_name="L"
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_superuser_rejects_is_staff_false(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="m@example.com",
                password="pass12345",
                full_name="M",
                is_staff=False,
            )

    def test_get_by_natural_key_is_case_insensitive(self):
        User.objects.create_user(
            email="n@example.com", password="pass12345", full_name="N"
        )
        found = User.objects.get_by_natural_key("N@Example.com")
        self.assertEqual(found.email, "n@example.com")

    def test_default_manager_is_unfiltered(self):
        user = User.objects.create_user(
            email="o@example.com", password="pass12345", full_name="O"
        )
        user.delete()
        self.assertIn(user, User.objects.all())
