from django.test import TestCase

from apps.universities.models import University
from apps.universities.serializers import (
    UniversityAdminWriteSerializer,
    UniversitySerializer,
)


class UniversitySerializerTests(TestCase):
    def test_read_serializer_exposes_expected_fields(self):
        university = University.objects.create(
            name="Serializer Test University",
            short_name="STU",
            logo="https://example.com/logo.png",
        )
        data = UniversitySerializer(university).data
        self.assertEqual(
            set(data.keys()),
            {
                "id",
                "name",
                "short_name",
                "slug",
                "logo",
                "is_active",
                "created_at",
                "updated_at",
            },
        )
        self.assertEqual(data["short_name"], "STU")
        self.assertEqual(data["slug"], "serializer-test-university")

    def test_read_serializer_is_fully_read_only(self):
        serializer = UniversitySerializer(data={"name": "X", "short_name": "X"})
        self.assertEqual(len(serializer.fields), 8)
        for field in serializer.fields.values():
            self.assertTrue(field.read_only)


class UniversityAdminWriteSerializerTests(TestCase):
    def test_valid_payload_is_accepted(self):
        serializer = UniversityAdminWriteSerializer(
            data={"name": "New University", "short_name": "NU"}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_is_active_is_not_a_writable_field(self):
        serializer = UniversityAdminWriteSerializer(
            data={"name": "New University", "short_name": "NU", "is_active": False}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("is_active", serializer.validated_data)

    def test_slug_is_not_a_writable_field(self):
        serializer = UniversityAdminWriteSerializer(
            data={"name": "New University", "short_name": "NU", "slug": "hacked-slug"}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("slug", serializer.validated_data)

    def test_duplicate_name_is_rejected(self):
        University.objects.create(name="Existing University", short_name="EU")
        serializer = UniversityAdminWriteSerializer(
            data={"name": "Existing University", "short_name": "NEW"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_duplicate_short_name_is_rejected(self):
        University.objects.create(name="Existing University", short_name="EU")
        serializer = UniversityAdminWriteSerializer(
            data={"name": "Another University", "short_name": "EU"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("short_name", serializer.errors)

    def test_missing_required_fields_rejected(self):
        serializer = UniversityAdminWriteSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)
        self.assertIn("short_name", serializer.errors)

    def test_partial_update_excludes_current_instance_from_uniqueness_check(self):
        university = University.objects.create(name="Self Update Uni", short_name="SUU")
        serializer = UniversityAdminWriteSerializer(
            university, data={"short_name": "SUU"}, partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_partial_update_with_explicit_null_logo_clears_it(self):
        university = University.objects.create(
            name="Logo Clear Uni", short_name="LCU", logo="https://example.com/old.png"
        )
        serializer = UniversityAdminWriteSerializer(
            university, data={"logo": None}, partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIn("logo", serializer.validated_data)
        self.assertIsNone(serializer.validated_data["logo"])

    def test_partial_update_omitting_logo_key_leaves_it_out_of_validated_data(self):
        university = University.objects.create(
            name="Logo Untouched Uni",
            short_name="LUU",
            logo="https://example.com/keep.png",
        )
        serializer = UniversityAdminWriteSerializer(
            university, data={"short_name": "LUU2"}, partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("logo", serializer.validated_data)
