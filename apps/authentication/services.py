from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from apps.common.exceptions import ConflictError, NotFoundError
from apps.users.models import User

_token_generator = PasswordResetTokenGenerator()


class AuthService:
    @staticmethod
    def register(*, email, password, full_name, phone_number=""):
        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                password=password,
                full_name=full_name,
                phone_number=phone_number,
            )
        return user

    @staticmethod
    def initiate_password_reset(*, email):
        try:
            user = User.objects.get(email=email.lower(), is_active=True)
        except User.DoesNotExist:
            return

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = _token_generator.make_token(user)
        reset_base = getattr(
            settings,
            "FRONTEND_PASSWORD_RESET_URL",
            "https://uniagora.app/reset-password",
        )
        reset_url = f"{reset_base}?uid={uid}&token={token}"
        send_mail(
            subject="Reset your UniAGORA password",
            message=(
                "Use the link below to reset your UniAGORA password:\n\n"
                f"{reset_url}\n\n"
                "If you did not request this, you can safely ignore this email."
            ),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[user.email],
            fail_silently=True,
        )

    @staticmethod
    def confirm_password_reset(*, uidb64, token, new_password):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError) as exc:
            raise NotFoundError("Invalid password reset link.") from exc

        if not _token_generator.check_token(user, token):
            raise ConflictError("Invalid or expired password reset token.")

        with transaction.atomic():
            user.set_password(new_password)
            user.save(update_fields=["password", "updated_at"])
        return user
