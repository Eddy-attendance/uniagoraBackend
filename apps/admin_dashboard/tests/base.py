from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class AdminAPITestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user(
            email="admin@uniagora.test",
            password="StrongPass123!",
            full_name="Admin One",
            is_staff=True,
        )
        self.customer = User.objects.create_user(
            email="customer@uniagora.test",
            password="StrongPass123!",
            full_name="Customer One",
        )
