"""Serializers do app de autenticação.

Cobrem cadastro, login, logout, verificação de e-mail e redefinição de senha.
A validação de senha usa os validadores do Django configurados em
``AUTH_PASSWORD_VALIDATORS``.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User
from apps.users.serializers import UserSerializer

from .tokens import email_verification_token, password_reset_token


def _password_field(**kwargs) -> serializers.CharField:
    """Campo de senha padronizado (nunca ecoado e sem ``strip``)."""
    return serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
        **kwargs,
    )


def _user_from_uid(uid: str) -> User:
    """Decodifica o ``uid`` (base64) e devolve o usuário correspondente."""
    try:
        user_id = urlsafe_base64_decode(uid).decode()
        return User.objects.get(pk=user_id)
    except (ValueError, TypeError, OverflowError, User.DoesNotExist) as exc:
        raise serializers.ValidationError("Link inválido ou expirado.") from exc


# ---------------------------------------------------------------------------
# Cadastro
# ---------------------------------------------------------------------------
class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = _password_field()
    password_confirm = _password_field()

    def validate_email(self, value: str) -> str:
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Já existe uma conta com este e-mail.")
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "As senhas não coincidem."}
            )

        # Valida contra os validadores do Django usando um usuário temporário,
        # para que o ``UserAttributeSimilarityValidator`` funcione (e-mail/nome).
        candidate = User(
            email=attrs["email"],
            full_name=attrs.get("full_name", ""),
            phone=attrs.get("phone", ""),
        )
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs

    def create(self, validated_data: dict) -> User:
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        return User.objects.create_user(
            password=password,
            # A conta só entra em uso após a confirmação do e-mail.
            is_active=not settings.AUTH_REQUIRE_EMAIL_VERIFICATION,
            **validated_data,
        )


# ---------------------------------------------------------------------------
# Login / logout / refresh
# ---------------------------------------------------------------------------
class LoginSerializer(TokenObtainPairSerializer):
    """Login por e-mail + senha, com dados do usuário na resposta."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Claims úteis para o front-end sem consultar a API a cada request.
        token["email"] = user.email
        token["role"] = user.role
        token["full_name"] = user.full_name
        return token

    def validate(self, attrs: dict) -> dict:
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)

    def validate_refresh(self, value: str) -> str:
        try:
            RefreshToken(value)
        except TokenError as exc:
            raise serializers.ValidationError("Token inválido ou expirado.") from exc
        return value


# ---------------------------------------------------------------------------
# Verificação de e-mail
# ---------------------------------------------------------------------------
class VerifyEmailSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs: dict) -> dict:
        user = _user_from_uid(attrs["uid"])
        if not email_verification_token.check_token(user, attrs["token"]):
            raise serializers.ValidationError("Link inválido ou expirado.")
        attrs["user"] = user
        return attrs


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()


# ---------------------------------------------------------------------------
# Redefinição de senha
# ---------------------------------------------------------------------------
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = _password_field()
    new_password_confirm = _password_field()

    def validate(self, attrs: dict) -> dict:
        user = _user_from_uid(attrs["uid"])

        if not password_reset_token.check_token(user, attrs["token"]):
            raise serializers.ValidationError("Token inválido ou expirado.")

        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "As senhas não coincidem."}
            )

        try:
            validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": exc.messages}) from exc

        attrs["user"] = user
        return attrs


# ---------------------------------------------------------------------------
# Serializers auxiliares (documentação OpenAPI)
# ---------------------------------------------------------------------------
class MessageSerializer(serializers.Serializer):
    detail = serializers.CharField()


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = UserSerializer(read_only=True)


class RegisterResponseSerializer(MessageSerializer):
    user = UserSerializer(read_only=True)


class RefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)


class RefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
