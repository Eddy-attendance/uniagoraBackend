from django.db import connection, models
from django.test import TestCase
from django.test.utils import isolate_apps

from apps.common.mixins import AutoSlugMixin
from apps.common.models import BaseModel


@isolate_apps("apps.common")
class BaseModelBehaviourTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        class SampleThing(AutoSlugMixin, BaseModel):
            name = models.CharField(max_length=100)
            slug = models.SlugField(max_length=110, unique=True, blank=True)
            slug_source_field = "name"

            class Meta:
                app_label = "common"

        cls.SampleThing = SampleThing
        with connection.schema_editor() as editor:
            editor.create_model(SampleThing)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as editor:
            editor.delete_model(cls.SampleThing)
        super().tearDownClass()

    def test_id_is_a_uuid(self):
        obj = self.SampleThing.objects.create(name="Widget")
        self.assertEqual(len(str(obj.id)), 36)

    def test_created_and_updated_timestamps_are_set(self):
        obj = self.SampleThing.objects.create(name="Widget")
        self.assertIsNotNone(obj.created_at)
        self.assertIsNotNone(obj.updated_at)

    def test_default_manager_is_unfiltered_by_default(self):
        # Revised design (post CTO review): `objects` returns every row,
        # including soft-deleted ones, unless `.alive()` is called
        # explicitly. This is the behaviour under review in point #1.
        obj = self.SampleThing.objects.create(name="Widget")
        obj.delete()

        self.assertTrue(self.SampleThing.objects.filter(pk=obj.pk).exists())
        refreshed = self.SampleThing.objects.get(pk=obj.pk)
        self.assertTrue(refreshed.is_deleted)

    def test_alive_excludes_soft_deleted_rows(self):
        obj = self.SampleThing.objects.create(name="Widget")
        obj.delete()

        self.assertFalse(self.SampleThing.objects.alive().filter(pk=obj.pk).exists())

    def test_dead_returns_only_soft_deleted_rows(self):
        alive_obj = self.SampleThing.objects.create(name="Alive")
        deleted_obj = self.SampleThing.objects.create(name="Deleted")
        deleted_obj.delete()

        dead_pks = set(self.SampleThing.objects.dead().values_list("pk", flat=True))
        self.assertEqual(dead_pks, {deleted_obj.pk})
        self.assertNotIn(alive_obj.pk, dead_pks)

    def test_hard_delete_removes_row_entirely(self):
        obj = self.SampleThing.objects.create(name="Widget")
        obj.delete(hard=True)

        self.assertFalse(self.SampleThing.objects.filter(pk=obj.pk).exists())

    def test_restore_reverses_soft_delete(self):
        obj = self.SampleThing.objects.create(name="Widget")
        obj.delete()
        obj.restore()

        self.assertFalse(self.SampleThing.objects.get(pk=obj.pk).is_deleted)

    def test_queryset_bulk_delete_soft_deletes(self):
        self.SampleThing.objects.create(name="Widget")
        self.SampleThing.objects.all().delete()

        # Unfiltered manager still sees the row (now flagged); .alive()
        # correctly excludes it.
        self.assertEqual(self.SampleThing.objects.count(), 1)
        self.assertEqual(self.SampleThing.objects.alive().count(), 0)

    def test_queryset_hard_delete_removes_rows_entirely(self):
        self.SampleThing.objects.create(name="Widget")
        self.SampleThing.objects.all().hard_delete()

        self.assertEqual(self.SampleThing.objects.count(), 0)

    def test_autoslug_generates_slug_from_source_field(self):
        obj = self.SampleThing.objects.create(name="Blue Bottle Coffee")
        self.assertEqual(obj.slug, "blue-bottle-coffee")

    def test_autoslug_deduplicates_on_collision(self):
        first = self.SampleThing.objects.create(name="Blue Bottle Coffee")
        second = self.SampleThing.objects.create(name="Blue Bottle Coffee")

        self.assertEqual(first.slug, "blue-bottle-coffee")
        self.assertEqual(second.slug, "blue-bottle-coffee-1")

    def test_autoslug_does_not_overwrite_an_explicit_slug(self):
        obj = self.SampleThing.objects.create(name="Widget", slug="custom-slug")
        self.assertEqual(obj.slug, "custom-slug")

    def test_autoslug_considers_soft_deleted_rows_when_checking_uniqueness(self):
        # A slug must never be reissued to a new live row just because its
        # previous holder was soft-deleted — this is precisely why the
        # uniqueness check in AutoSlugMixin uses the unfiltered `objects`
        # manager rather than `.alive()`.
        first = self.SampleThing.objects.create(name="Blue Bottle Coffee")
        first.delete()

        second = self.SampleThing.objects.create(name="Blue Bottle Coffee")
        self.assertEqual(second.slug, "blue-bottle-coffee-1")
