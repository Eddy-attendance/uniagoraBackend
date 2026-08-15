from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.filters import ActiveUniversityFilterBackend


def make_request(user):
    return SimpleNamespace(user=user)


def make_user(is_authenticated=True, active_university=None):
    return SimpleNamespace(
        is_authenticated=is_authenticated, active_university=active_university
    )


class ActiveUniversityFilterBackendTests(SimpleTestCase):
    def setUp(self):
        self.backend = ActiveUniversityFilterBackend()
        self.queryset = MagicMock(name="queryset")

    def test_authenticated_user_with_active_university_filters_by_it(self):
        university = SimpleNamespace(name="University of Ibadan")
        request = make_request(make_user(active_university=university))
        view = SimpleNamespace()

        result = self.backend.filter_queryset(request, self.queryset, view)

        self.queryset.filter.assert_called_once_with(university=university)
        self.assertIs(result, self.queryset.filter.return_value)
        self.queryset.none.assert_not_called()

    def test_view_can_override_lookup_field(self):
        university = SimpleNamespace(name="UI")
        request = make_request(make_user(active_university=university))
        view = SimpleNamespace(
            university_lookup_field="store__vendor_profile__university"
        )

        self.backend.filter_queryset(request, self.queryset, view)

        self.queryset.filter.assert_called_once_with(
            store__vendor_profile__university=university
        )

    def test_default_lookup_field_is_university(self):
        self.assertEqual(
            ActiveUniversityFilterBackend.university_lookup_field, "university"
        )

    def test_anonymous_user_gets_empty_queryset(self):
        request = make_request(make_user(is_authenticated=False))
        view = SimpleNamespace()

        result = self.backend.filter_queryset(request, self.queryset, view)

        self.queryset.none.assert_called_once()
        self.assertIs(result, self.queryset.none.return_value)
        self.queryset.filter.assert_not_called()

    def test_user_without_active_university_gets_empty_queryset(self):
        request = make_request(make_user(active_university=None))
        view = SimpleNamespace()

        result = self.backend.filter_queryset(request, self.queryset, view)

        self.queryset.none.assert_called_once()
        self.assertIs(result, self.queryset.none.return_value)
        self.queryset.filter.assert_not_called()

    def test_missing_user_on_request_gets_empty_queryset(self):
        request = make_request(user=None)
        view = SimpleNamespace()

        result = self.backend.filter_queryset(request, self.queryset, view)

        self.queryset.none.assert_called_once()
        self.assertIs(result, self.queryset.none.return_value)
