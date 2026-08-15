from types import SimpleNamespace

from django.test import SimpleTestCase
from rest_framework.permissions import BasePermission

from apps.core.permissions import (
    IsAdmin,
    IsAuthenticatedCustomer,
    IsOwnerVendor,
    IsVerifiedVendor,
)


def make_request(user):
    return SimpleNamespace(user=user)


def make_user(
    is_authenticated=True,
    is_staff=False,
    is_superuser=False,
    vendor_profile=None,
):
    return SimpleNamespace(
        is_authenticated=is_authenticated,
        is_staff=is_staff,
        is_superuser=is_superuser,
        vendor_profile=vendor_profile,
    )


class FakeVendorProfile:
    """
    Minimal stand-in for `vendors.VendorProfile`.
    """

    def __init__(self, pk="vendor-1", is_verified=True):
        self.pk = pk
        self.is_verified = is_verified

    def __eq__(self, other):
        if not isinstance(other, FakeVendorProfile):
            return NotImplemented
        return self.pk == other.pk

    def __hash__(self):
        return hash(self.pk)


def make_vendor_profile(pk="vendor-1", is_verified=True):
    return FakeVendorProfile(pk=pk, is_verified=is_verified)


class IsAuthenticatedCustomerTests(SimpleTestCase):
    """Every registered account is automatically a Customer."""

    def setUp(self):
        self.permission = IsAuthenticatedCustomer()

    def test_authenticated_user_is_allowed(self):
        request = make_request(make_user(is_authenticated=True))
        self.assertTrue(self.permission.has_permission(request, view=None))

    def test_anonymous_user_is_denied(self):
        request = make_request(make_user(is_authenticated=False))
        self.assertFalse(self.permission.has_permission(request, view=None))

    def test_missing_user_on_request_is_denied(self):
        request = make_request(user=None)
        self.assertFalse(self.permission.has_permission(request, view=None))


class IsVerifiedVendorTests(SimpleTestCase):
    """Authenticated + VendorProfile.status == VERIFIED."""

    def setUp(self):
        self.permission = IsVerifiedVendor()

    def test_verified_vendor_is_allowed(self):
        vendor_profile = make_vendor_profile(is_verified=True)
        request = make_request(make_user(vendor_profile=vendor_profile))
        self.assertTrue(self.permission.has_permission(request, view=None))

    def test_unverified_or_suspended_vendor_is_denied(self):
        vendor_profile = make_vendor_profile(is_verified=False)
        request = make_request(make_user(vendor_profile=vendor_profile))
        self.assertFalse(self.permission.has_permission(request, view=None))

    def test_customer_with_no_vendor_profile_is_denied(self):
        request = make_request(make_user(vendor_profile=None))
        self.assertFalse(self.permission.has_permission(request, view=None))

    def test_anonymous_user_is_denied(self):
        vendor_profile = make_vendor_profile(is_verified=True)
        request = make_request(
            make_user(is_authenticated=False, vendor_profile=vendor_profile)
        )
        self.assertFalse(self.permission.has_permission(request, view=None))


class IsOwnerVendorTests(SimpleTestCase):
    """
    Object-level ownership check, never trusting a client-supplied vendor/store ID.
    """

    def setUp(self):
        self.permission = IsOwnerVendor()

    def test_has_permission_is_not_overridden(self):
        self.assertIs(IsOwnerVendor.has_permission, BasePermission.has_permission)

    def test_has_permission_default_is_unconditionally_true(self):
        request = make_request(user=None)
        self.assertTrue(self.permission.has_permission(request, view=None))

    def test_object_level_allows_matching_store_owner(self):
        request_vendor_profile = make_vendor_profile(pk="vendor-1")
        request = make_request(make_user(vendor_profile=request_vendor_profile))
        store_obj = SimpleNamespace(vendor_profile=make_vendor_profile(pk="vendor-1"))
        self.assertTrue(self.permission.has_object_permission(request, None, store_obj))

    def test_object_level_allows_matching_product_owner_via_store(self):
        request_vendor_profile = make_vendor_profile(pk="vendor-1")
        request = make_request(make_user(vendor_profile=request_vendor_profile))
        product_obj = SimpleNamespace(
            store=SimpleNamespace(vendor_profile=make_vendor_profile(pk="vendor-1"))
        )
        self.assertTrue(
            self.permission.has_object_permission(request, None, product_obj)
        )

    def test_object_level_treats_same_pk_as_same_owner_regardless_of_other_fields(self):
        request_vendor_profile = make_vendor_profile(pk="vendor-1", is_verified=True)
        request = make_request(make_user(vendor_profile=request_vendor_profile))
        store_obj = SimpleNamespace(
            vendor_profile=make_vendor_profile(pk="vendor-1", is_verified=False)
        )
        self.assertTrue(self.permission.has_object_permission(request, None, store_obj))

    def test_object_level_denies_different_vendor(self):
        request_vendor_profile = make_vendor_profile(pk="vendor-1")
        request = make_request(make_user(vendor_profile=request_vendor_profile))
        store_obj = SimpleNamespace(vendor_profile=make_vendor_profile(pk="vendor-2"))
        self.assertFalse(
            self.permission.has_object_permission(request, None, store_obj)
        )

    def test_object_level_ignores_client_supplied_identifiers(self):
        request_vendor_profile = make_vendor_profile(pk="vendor-1")
        request = make_request(make_user(vendor_profile=request_vendor_profile))
        store_obj = SimpleNamespace(
            vendor_profile=make_vendor_profile(pk="vendor-2"),
            requested_vendor_id="vendor-1",  # attacker-supplied, must be ignored
        )
        self.assertFalse(
            self.permission.has_object_permission(request, None, store_obj)
        )

    def test_object_level_denies_unrecognized_object_shape(self):
        request_vendor_profile = make_vendor_profile(pk="vendor-1")
        request = make_request(make_user(vendor_profile=request_vendor_profile))
        unrelated_obj = SimpleNamespace(some_other_field=True)
        self.assertFalse(
            self.permission.has_object_permission(request, None, unrelated_obj)
        )

    def test_object_level_denies_anonymous_user(self):
        request = make_request(make_user(is_authenticated=False))
        store_obj = SimpleNamespace(vendor_profile=make_vendor_profile())
        self.assertFalse(
            self.permission.has_object_permission(request, None, store_obj)
        )

    def test_object_level_denies_when_requester_has_no_vendor_profile(self):
        request = make_request(make_user(vendor_profile=None))
        store_obj = SimpleNamespace(vendor_profile=make_vendor_profile())
        self.assertFalse(
            self.permission.has_object_permission(request, None, store_obj)
        )


class IsAdminTests(SimpleTestCase):
    """IsAdmin — is_staff/is_superuser."""

    def setUp(self):
        self.permission = IsAdmin()

    def test_staff_user_is_allowed(self):
        request = make_request(make_user(is_staff=True))
        self.assertTrue(self.permission.has_permission(request, view=None))

    def test_superuser_is_allowed(self):
        request = make_request(make_user(is_superuser=True))
        self.assertTrue(self.permission.has_permission(request, view=None))

    def test_regular_customer_is_denied(self):
        request = make_request(make_user())
        self.assertFalse(self.permission.has_permission(request, view=None))

    def test_anonymous_staff_flag_is_denied(self):
        request = make_request(make_user(is_authenticated=False, is_staff=True))
        self.assertFalse(self.permission.has_permission(request, view=None))

    def test_missing_user_on_request_is_denied(self):
        request = make_request(user=None)
        self.assertFalse(self.permission.has_permission(request, view=None))
