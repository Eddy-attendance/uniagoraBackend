from apps.common.exceptions import ConflictError


class UserService:
    @staticmethod
    def update_profile(*, user, full_name=None, phone_number=None):
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
