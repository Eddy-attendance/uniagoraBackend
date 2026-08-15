from decimal import Decimal

from apps.categories.models import Category
from apps.products.models import Product, ProductCondition
from apps.stores.models import Store
from apps.universities.models import University
from apps.users.models import User
from apps.vendors.models import VendorProfile, VendorStatus, VendorType

DEFAULT_PASSWORD = "Testpass123!"


def make_university(**kwargs):
    defaults = {"name": "Test University", "short_name": "TU"}
    defaults.update(kwargs)
    return University.objects.create(**defaults)


def make_customer(university=None, email="customer@example.com", **kwargs):
    defaults = {
        "email": email,
        "password": DEFAULT_PASSWORD,
        "full_name": "Test Customer",
        "active_university": university,
    }
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def make_admin(email="admin@example.com", **kwargs):
    defaults = {
        "email": email,
        "password": DEFAULT_PASSWORD,
        "full_name": "Test Admin",
        "is_staff": True,
    }
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def make_verified_vendor(
    university, email="vendor@example.com", store_name="Test Store", **kwargs
):
    """Returns (user, vendor_profile, store) — a fully verified vendor with an
    owned Store, ready to own Products."""
    user = make_customer(university=university, email=email, full_name="Test Vendor")
    vp_defaults = {
        "user": user,
        "university": university,
        "vendor_type": VendorType.STUDENT,
        "store_name": store_name,
        "phone_number": "+2348012345678",
        "matric_number": kwargs.pop("matric_number", "MAT/0001"),
        "department": "Computer Science",
        "level": "300",
        "status": VendorStatus.VERIFIED,
    }
    vp_defaults.update(kwargs)
    vendor_profile = VendorProfile.objects.create(**vp_defaults)
    store = Store.objects.create(
        vendor_profile=vendor_profile,
        display_name=store_name,
        contact_phone=vendor_profile.phone_number,
    )
    return user, vendor_profile, store


def make_category(name="Electronics", **kwargs):
    defaults = {"name": name}
    defaults.update(kwargs)
    return Category.objects.create(**defaults)


def make_product(store, university, **kwargs):
    defaults = {
        "store": store,
        "university": university,
        "name": "Test Product",
        "description": "A perfectly ordinary test product.",
        "price": Decimal("100.00"),
        "condition": ProductCondition.NEW,
        "quantity": 5,
    }
    defaults.update(kwargs)
    return Product.objects.create(**defaults)
