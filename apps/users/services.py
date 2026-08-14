"""Service layer for apps.users — profile updates and active-university
selection (DDS §3: "users owns... active_university selection").
"""

from apps.common.exceptions import ConflictError


class UserService:
    @staticmethod
    def update_profile(*, user, full_name=None, phone_number=None):
        """Updates only the fields explicitly provided, mirroring the
        pattern `UniversityService.update` already establishes
        (universities EDD §7) — never touches fields outside this narrow,
        named set.
        """
        update_fields = []
        if full_name is not None:
            user.full_name = full_name
            update_fields.append("full_name")
        if phone_number is not None:
            user.phone_number = phone_number
            update_fields.append("phone_number")
        if update_fields:
            update_fields.append("updated_at")
            user.save(update_fields=update_fields)
        return user

    @staticmethod
    def set_active_university(*, user, university):
        """PRD §3: "Users may change their university whenever they wish."

        Rejecting a currently-inactive university at selection time is an
        Engineering Implementation Decision (EDD §10, assumption 2) — no
        frozen document states this explicitly, but it mirrors DDS §4.1's
        "inactive universities are hidden from onboarding" intent. An
        existing assignment to a university that later becomes inactive is
        left untouched (no cascade), consistent with the universities EDD's
        own confirmed no-cascade-on-deactivation decision (ADR-U... /
        universities EDD §7, §9 assumption 2).
        """
        if not university.is_active:
            raise ConflictError("Cannot select an inactive university.")
        user.active_university = university
        user.save(update_fields=["active_university", "updated_at"])
        return user

    @staticmethod
    def activate(*, user):
        if user.is_active:
            raise ConflictError("User is already active.")

        user.is_active = True
        user.save(update_fields=["is_active", "updated_at"])
        return user

    @staticmethod
    def deactivate(*, user):
        if not user.is_active:
            raise ConflictError("User is already inactive.")

        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        return user
