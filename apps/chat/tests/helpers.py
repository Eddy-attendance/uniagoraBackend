from apps.products.models import Product, ProductCondition
from apps.stores.models import Store
from apps.universities.models import University
from apps.users.models import User
from apps.vendors.models import VendorProfile, VendorStatus, VendorType


def make_university(**kwargs):
    """Create a valid active university fixture."""
    defaults = {
        "name": f"University of Ibadan {University.objects.count()}",
        "short_name": f"UI{University.objects.count()}",
        "is_active": True,
    }
    defaults.update(kwargs)
    return University.objects.create(**defaults)


def make_user(email=None, university=None, **kwargs):
    """
    Create a valid user fixture.

    `active_university` is populated when a university is supplied so the
    fixture behaves like a normally onboarded UniAGORA user.
    """
    if email is None:
        email = f"user{User.objects.count()}@example.com"

    if university is None:
        university = kwargs.pop("active_university", None)

    defaults = {
        "email": email,
        "full_name": "Test User",
        "password": "TestPass123!",
    }

    if university is not None:
        defaults["active_university"] = university

    defaults.update(kwargs)

    password = defaults.pop("password")
    return User.objects.create_user(password=password, **defaults)


def make_vendor(
    user=None,
    university=None,
    status=VendorStatus.VERIFIED,
    **kwargs,
):
    """
    Create a valid vendor fixture with its required user/university
    relationship.

    The default status is VERIFIED because most chat flows require an
    eligible vendor.
    """
    if university is None:
        university = kwargs.pop("vendor_university", None) or make_university()

    if user is None:
        user = make_user(
            email=f"vendor{VendorProfile.objects.count()}@example.com",
            university=university,
        )

    defaults = {
        "user": user,
        "university": university,
        "vendor_type": VendorType.STUDENT,
        "store_name": "Test Store",
        "phone_number": "+2348012345678",
        "matric_number": f"MAT{VendorProfile.objects.count():04d}",
        "department": "Computer Science",
        "level": "300",
        "status": status,
    }

    defaults.update(kwargs)

    return VendorProfile.objects.create(**defaults)


def make_store(vendor_profile=None, **kwargs):
    """Create a store belonging to a real vendor profile."""
    vendor_profile = vendor_profile or make_vendor()

    defaults = {
        "vendor_profile": vendor_profile,
        "display_name": vendor_profile.store_name,
        "contact_phone": vendor_profile.phone_number,
    }

    defaults.update(kwargs)

    return Store.objects.create(**defaults)


def make_product(store=None, university=None, **kwargs):
    """
    Create a product belonging to the supplied store.
    """
    store = store or make_store()

    if university is None:
        university = store.vendor_profile.university

    defaults = {
        "store": store,
        "university": university,
        "name": "Test Product",
        "description": "A test product.",
        "price": "1000.00",
        "condition": ProductCondition.NEW,
        "quantity": 1,
    }

    defaults.update(kwargs)

    return Product.objects.create(**defaults)
