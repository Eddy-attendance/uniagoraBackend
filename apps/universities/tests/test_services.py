from django.test import TestCase

from apps.common.exceptions import ConflictError
from apps.universities.models import University
from apps.universities.services import UniversityService


class UniversityServiceCreateTests(TestCase):
    def test_create_persists_university(self):
        university = UniversityService.create(
            name="Service Created Uni", short_name="SCU"
        )
        self.assertIsNotNone(university.pk)
        self.assertEqual(university.name, "Service Created Uni")
        self.assertTrue(university.is_active)

    def test_create_triggers_slug_generation(self):
        university = UniversityService.create(name="Slug Gen Uni", short_name="SGU")
        self.assertEqual(university.slug, "slug-gen-uni")


class UniversityServiceUpdateTests(TestCase):
    def setUp(self):
        self.university = University.objects.create(
            name="Original Name", short_name="ORIG"
        )

    def test_update_changes_only_provided_fields(self):
        updated = UniversityService.update(
            university=self.university, short_name="NEWSN"
        )
        self.assertEqual(updated.name, "Original Name")
        self.assertEqual(updated.short_name, "NEWSN")

    def test_update_does_not_touch_slug(self):
        original_slug = self.university.slug
        updated = UniversityService.update(
            university=self.university, name="Renamed University"
        )
        self.assertEqual(updated.slug, original_slug)

    def test_update_does_not_touch_is_active(self):
        updated = UniversityService.update(
            university=self.university, name="Renamed Again"
        )
        self.assertTrue(updated.is_active)

    def test_update_can_change_logo(self):
        updated = UniversityService.update(
            university=self.university, logo="https://example.com/new-logo.png"
        )
        self.assertEqual(updated.logo, "https://example.com/new-logo.png")

    def test_update_omitting_logo_leaves_existing_logo_untouched(self):
        self.university.logo = "https://example.com/keep-me.png"
        self.university.save(update_fields=["logo"])

        updated = UniversityService.update(
            university=self.university, short_name="ORIG2"
        )

        self.assertEqual(updated.logo, "https://example.com/keep-me.png")

    def test_update_with_explicit_none_logo_clears_it(self):
        self.university.logo = "https://example.com/remove-me.png"
        self.university.save(update_fields=["logo"])

        updated = UniversityService.update(university=self.university, logo=None)

        self.assertIsNone(updated.logo)

    def test_update_with_no_kwargs_at_all_leaves_every_field_untouched(self):
        self.university.logo = "https://example.com/stable.png"
        self.university.save(update_fields=["logo"])

        updated = UniversityService.update(university=self.university)

        self.assertEqual(updated.name, "Original Name")
        self.assertEqual(updated.short_name, "ORIG")
        self.assertEqual(updated.logo, "https://example.com/stable.png")


class UniversityServiceActivationTests(TestCase):
    def setUp(self):
        self.university = University.objects.create(
            name="Lifecycle Uni", short_name="LU"
        )

    def test_deactivate_sets_is_active_false(self):
        UniversityService.deactivate(university=self.university)
        self.university.refresh_from_db()
        self.assertFalse(self.university.is_active)

    def test_deactivate_twice_raises_conflict_error(self):
        UniversityService.deactivate(university=self.university)
        with self.assertRaises(ConflictError):
            UniversityService.deactivate(university=self.university)

    def test_activate_sets_is_active_true(self):
        UniversityService.deactivate(university=self.university)
        UniversityService.activate(university=self.university)
        self.university.refresh_from_db()
        self.assertTrue(self.university.is_active)

    def test_activate_already_active_raises_conflict_error(self):
        with self.assertRaises(ConflictError):
            UniversityService.activate(university=self.university)

    def test_conflict_error_carries_409_status(self):
        try:
            UniversityService.activate(university=self.university)
        except ConflictError as exc:
            self.assertEqual(exc.status_code, 409)
        else:
            self.fail("ConflictError was not raised")

    def test_deactivate_does_not_soft_delete(self):
        UniversityService.deactivate(university=self.university)
        self.university.refresh_from_db()
        self.assertFalse(self.university.is_deleted)
