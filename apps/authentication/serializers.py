from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.exceptions import ConflictError, PermissionDeniedError
from apps.common.validators import validate_phone_number
from apps.users.models import User
from apps.users.serializers import UserSerializer


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    full_name = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        allow_null=False,
        validators=[validate_phone_number],
    )

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return value


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def save(self, **kwargs):
        request = self.context["request"]
        try:
            token = RefreshToken(self.validated_data["refresh"])
        except TokenError as exc:
            raise ConflictError(
                "Invalid or already-invalidated refresh token."
            ) from exc

        token_user_id = str(token.get(jwt_settings.USER_ID_CLAIM))
        if token_user_id != str(request.user.id):
            raise PermissionDeniedError(
                "This refresh token does not belong to the requesting user."
            )

        token.blacklist()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True, validators=[validate_password]
    )
