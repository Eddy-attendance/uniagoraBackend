"""
apps/chat/services/conversation_service.py

Business logic for Conversation initiation and transaction completion,
per DDS §10 ("Conversation | ConversationService | Initiation rule,
transaction-completion marking"). Views never contain this logic
(Architecture §7); this is the single call path for both the REST view
and (indirectly, for message-side effects) the WebSocket consumer.
"""

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.chat.models import Conversation, TransactionStatus
from apps.common.exceptions import (
    ApplicationError,
    ConflictError,
    PermissionDeniedError,
)
from apps.vendors.models import VendorProfile


class ConversationService:
    """Stateless service — see Architecture §7 (services are plain
    functions/thin stateless classes, not model methods, once an
    operation has side effects or spans more than one concern)."""

    @staticmethod
    @transaction.atomic
    def initiate(*, customer, vendor, product=None):
        """
        Create (or return an already-existing identical) Conversation
        initiated by `customer` towards `vendor`, optionally scoped to
        `product`. Returns `(conversation, created)` — CTO review fix:
        the view needs to know whether a row was actually created to
        return 201 vs 200 (see `views.py::ConversationViewSet.create`).

        Enforcement:
        - `vendor` must be VERIFIED — Engineering Decision, chat README
          Assumption 2.
        - a vendor may not message their own store as a customer —
          Engineering Decision, chat README Assumption 3.
        - `product`, if given, must belong to `vendor`'s own store
          (serializer-level check is the friendly path; this is the
          service-layer backstop, DDS §7.2's documented pattern).
        - idempotent: an existing matching (customer, vendor, product)
          conversation is returned rather than duplicated or erroring —
          chat README Assumption 4.
        - PRD §10 ("Vendors cannot start conversations with Customers")
          is satisfied structurally: `customer` is always the requesting
          user, never accepted as client input at any layer above this
          service — there is no code path by which a vendor "initiates
          as vendor".

        Concurrency (CTO review fix): initiation is serialized per-vendor
        via `SELECT ... FOR UPDATE` on the target `VendorProfile` row,
        held for the duration of this atomic block. `VendorProfile` is
        the existing entity every conversation-for-this-vendor request
        already references — locking it (rather than inventing a new
        synchronization primitive, e.g. an advisory lock or a Redis
        mutex) makes the check-then-create sequence below atomic across
        concurrent requests targeting the same vendor, including the
        product-less case where PostgreSQL's NULL-distinct behavior means
        the DB unique constraint alone cannot prevent a duplicate (DDS
        §13 Assumption 7). Every conversation-creating code path in this
        codebase goes through this service, so the lock reliably
        serializes all conversation creation for a given vendor; the
        `IntegrityError` handling below is a defensive backstop for any
        write path outside this service (e.g. a data migration, an admin
        shell), not the primary correctness mechanism.

        This does mean two customers concurrently messaging the same
        popular vendor about *different* products briefly serialize on
        this one row. At MVP scale (a vendor's own store's applications
        submitted synchronously, no bulk-messaging feature) this is an
        acceptable, deliberately narrow trade-off — a genuinely
        higher-throughput future need would call for a finer-grained
        lock (e.g. keyed on `(customer, vendor)` via `select_for_update`
        on a dedicated lock row), which is not warranted by anything in
        the frozen documents today.
        """
        # Row lock acquired first so every check below (including
        # `is_verified`) reads a value that cannot change out from under
        # this request for the rest of the transaction.
        locked_vendor = VendorProfile.objects.select_for_update().get(pk=vendor.pk)

        if not locked_vendor.is_verified:
            raise ConflictError("This vendor is not currently accepting messages.")

        if getattr(locked_vendor, "user_id", None) == getattr(customer, "id", None):
            raise ConflictError("You cannot start a conversation with your own store.")

        if product is not None and product.store.vendor_profile_id != locked_vendor.id:
            raise ApplicationError(
                "The selected product does not belong to this vendor.",
                errors={
                    "product": ["Product does not belong to the specified vendor."]
                },
            )

        existing = (
            Conversation.objects.alive()
            .filter(customer=customer, vendor=locked_vendor, product=product)
            .first()
        )
        if existing is not None:
            return existing, False

        try:
            # Nested atomic (SAVEPOINT): if the INSERT hits the unique
            # constraint despite the lock/pre-check above (the
            # outside-this-service race described above), only this
            # savepoint rolls back — the outer transaction (and the
            # vendor row lock it holds) stays valid so the fallback
            # lookup below can still run and commit cleanly.
            with transaction.atomic():
                conversation = Conversation.objects.create(
                    customer=customer, vendor=locked_vendor, product=product
                )
            return conversation, True
        except IntegrityError:
            existing = (
                Conversation.objects.alive()
                .filter(customer=customer, vendor=locked_vendor, product=product)
                .first()
            )
            if existing is not None:
                return existing, False
            raise

    @staticmethod
    @transaction.atomic
    def mark_completed(*, conversation, actor):
        """
        Vendor-only transition: ONGOING -> COMPLETED (DDS §9.5). No path
        back to ONGOING exists in MVP — completion is terminal.

        Concurrency (CTO review fix): the target `Conversation` row is
        locked via `SELECT ... FOR UPDATE` before its status is read, so
        two concurrent completion requests cannot both observe `ONGOING`
        and both attempt the transition. The second request blocks on
        the lock until the first commits, then re-reads the now-
        `COMPLETED` row and correctly raises `ConflictError` — the same
        row-locking approach already used by `ConversationService
        .initiate()` for its own concurrency fix, applied here to the
        one row that already exists and is already being mutated, per
        that fix's own "lock an existing entity, don't invent a new
        synchronization model" precedent.
        """
        locked_conversation = (
            Conversation.objects.select_for_update()
            .select_related("vendor")
            .get(pk=conversation.pk)
        )

        if getattr(locked_conversation.vendor, "user_id", None) != getattr(
            actor, "id", None
        ):
            raise PermissionDeniedError(
                "Only the vendor of this conversation may mark the transaction as completed."
            )

        if locked_conversation.transaction_status == TransactionStatus.COMPLETED:
            raise ConflictError("This transaction has already been marked completed.")

        locked_conversation.transaction_status = TransactionStatus.COMPLETED
        locked_conversation.completed_at = timezone.now()
        locked_conversation.save(
            update_fields=["transaction_status", "completed_at", "updated_at"]
        )
        return locked_conversation
