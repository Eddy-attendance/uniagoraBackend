from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import ConflictError
from apps.products.services.lifecycle_service import ProductLifecycleService

from .models import (
    VendorDocument,
    VendorDocumentStatus,
    VendorProfile,
    VendorStatus,
    VendorType,
)


class VendorDocumentService:
    """One document per vendor in MVP flow"""

    @staticmethod
    def create_for_vendor(*, vendor_profile, document_type, file):
        if vendor_profile.documents.exists():
            raise ConflictError("Vendor already has a submitted document.")
        document = VendorDocument.objects.create(
            vendor_profile=vendor_profile,
            document_type=document_type,
            file=file,
        )
        document.status = VendorDocumentStatus.APPROVED
        document.reviewed_at = timezone.now()
        document.save(update_fields=["status", "reviewed_at", "updated_at"])
        return document


class VendorVerificationService:
    """Status transitions out of PENDING"""

    @staticmethod
    def approve(*, vendor_profile, reviewed_by=None):
        if vendor_profile.status != VendorStatus.PENDING:
            raise ConflictError("Only a pending application can be approved.")
        vendor_profile.status = VendorStatus.VERIFIED
        vendor_profile.reviewed_at = timezone.now()
        vendor_profile.reviewed_by = reviewed_by
        vendor_profile.save(
            update_fields=["status", "reviewed_at", "reviewed_by", "updated_at"]
        )
        return vendor_profile

    @staticmethod
    def reject(*, vendor_profile, reviewed_by):
        if vendor_profile.status != VendorStatus.PENDING:
            raise ConflictError("Only a pending application can be rejected.")
        vendor_profile.status = VendorStatus.REJECTED
        vendor_profile.reviewed_at = timezone.now()
        vendor_profile.reviewed_by = reviewed_by
        vendor_profile.save(
            update_fields=["status", "reviewed_at", "reviewed_by", "updated_at"]
        )
        return vendor_profile


class VendorSuspensionService:
    """Admin-triggered suspend/reinstate (DDS §9.2, §10)."""

    @staticmethod
    @transaction.atomic
    def suspend(*, vendor_profile):
        if vendor_profile.status != VendorStatus.VERIFIED:
            raise ConflictError("Only a verified vendor can be suspended.")

        vendor_profile.status = VendorStatus.SUSPENDED
        vendor_profile.save(update_fields=["status", "updated_at"])

        from apps.stores.services import StoreService

        try:
            store = vendor_profile.store
        except VendorProfile.store.RelatedObjectDoesNotExist:
            store = None

        if store is not None:
            StoreService.set_active_state(
                store=store,
                is_active=False,
            )
            # Product suspension cascade.
            ProductLifecycleService.suspend_store_products(store=store)
        return vendor_profile

    @staticmethod
    @transaction.atomic
    def reinstate(*, vendor_profile):
        if vendor_profile.status != VendorStatus.SUSPENDED:
            raise ConflictError("Only a suspended vendor can be reinstated.")

        vendor_profile.status = VendorStatus.VERIFIED
        vendor_profile.save(update_fields=["status", "updated_at"])

        from apps.stores.services import StoreService

        try:
            store = vendor_profile.store
        except VendorProfile.store.RelatedObjectDoesNotExist:
            store = None

        if store is not None:
            StoreService.set_active_state(
                store=store,
                is_active=True,
            )
            # Product reinstatement cascade
            ProductLifecycleService.reinstate_store_products(store=store)
        return vendor_profile


class VendorApplicationService:
    """Application intake. Creates VendorProfile (+ document for
    STUDENT vendors) and auto-approves in the same transaction."""

    @staticmethod
    @transaction.atomic
    def apply(
        *,
        user,
        university,
        vendor_type,
        store_name,
        phone_number,
        matric_number=None,
        department=None,
        level=None,
        business_name=None,
        business_address=None,
        business_logo=None,
        document_type=None,
        document_file=None,
    ):
        if hasattr(user, "vendor_profile"):
            raise ConflictError("This account already has a vendor profile.")

        vendor_profile = VendorProfile.objects.create(
            user=user,
            university=university,
            vendor_type=vendor_type,
            store_name=store_name,
            phone_number=phone_number,
            matric_number=matric_number if vendor_type == VendorType.STUDENT else None,
            department=department if vendor_type == VendorType.STUDENT else None,
            level=level if vendor_type == VendorType.STUDENT else None,
            business_name=business_name if vendor_type == VendorType.BUSINESS else None,
            business_address=business_address
            if vendor_type == VendorType.BUSINESS
            else None,
            business_logo=business_logo if vendor_type == VendorType.BUSINESS else None,
        )

        if vendor_type == VendorType.STUDENT:
            VendorDocumentService.create_for_vendor(
                vendor_profile=vendor_profile,
                document_type=document_type,
                file=document_file,
            )

        VendorVerificationService.approve(
            vendor_profile=vendor_profile, reviewed_by=None
        )
        vendor_profile.refresh_from_db()
        return vendor_profile
