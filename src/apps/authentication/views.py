"""Views do app de autenticação (JWT).

Rotas montadas em ``/api/auth/`` (ver ``urls.py``). Todas usam throttling
escopado (``ScopedRateThrottle``) para dificultar força bruta; os limites ficam
em ``REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`` e são configuráveis por ambiente.
"""

from __future__ import annotations

import logging

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.users.models import User
from apps.users.serializers import UserSerializer

from .emails import send_password_reset_email, send_verification_email
from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    MessageSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RefreshRequestSerializer,
    RefreshResponseSerializer,
    RegisterResponseSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    TokenPairSerializer,
    VerifyEmailSerializer,
)
from .services import blacklist_user_tokens

logger = logging.getLogger("findly.authentication")

# Mensagens genéricas: não revelam se um e-mail está cadastrado.
RESET_REQUESTED = (
    "Se o e-mail estiver cadastrado, enviaremos as instruções de redefinição."
)
VERIFICATION_RESENT = (
    "Se a conta existir e ainda não estiver verificada, enviaremos um novo e-mail."
)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    @extend_schema(
        request=RegisterSerializer,
        responses={201: RegisterResponseSerializer},
        description=(
            "Cria a conta. Com `AUTH_REQUIRE_EMAIL_VERIFICATION=True` (padrão), "
            "o usuário nasce inativo e recebe um e-mail de confirmação."
        ),
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        if settings.AUTH_REQUIRE_EMAIL_VERIFICATION:
            try:
                send_verification_email(user)
            except Exception:  # pragma: no cover - falha de SMTP não quebra o cadastro
                logger.exception(
                    "Falha ao enviar e-mail de verificação (user=%s).", user.pk
                )
            detail = "Conta criada. Verifique seu e-mail para ativá-la."
        else:
            detail = "Conta criada com sucesso."

        return Response(
            {"detail": detail, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        request=LoginSerializer,
        responses={200: TokenPairSerializer},
        description="Autentica por e-mail e senha e devolve `access` + `refresh`.",
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RefreshTokenView(TokenRefreshView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        request=RefreshRequestSerializer,
        responses={200: RefreshResponseSerializer},
        description=(
            "Renova o `access` a partir do `refresh`. Como a rotação está "
            "habilitada, o `refresh` usado é invalidado (blacklist)."
        ),
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        request=LogoutSerializer,
        responses={200: MessageSerializer},
        description="Invalida o `refresh` informado (blacklist).",
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = RefreshToken(serializer.validated_data["refresh"])
        # Um usuário autenticado só pode encerrar as próprias sessões.
        if str(token.payload.get("user_id")) != str(request.user.pk):
            raise ValidationError(
                {"refresh": "Este token não pertence ao usuário autenticado."}
            )
        token.blacklist()

        return Response({"detail": "Sessão encerrada com sucesso."})


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        request=VerifyEmailSerializer,
        responses={200: MessageSerializer},
        description="Ativa a conta a partir do `uid` e `token` recebidos por e-mail.",
    )
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        user.is_active = True
        user.save(update_fields=["is_active"])

        return Response({"detail": "E-mail verificado com sucesso."})


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    @extend_schema(
        request=ResendVerificationSerializer,
        responses={202: MessageSerializer},
        description="Reenvia o e-mail de confirmação para contas ainda inativas.",
    )
    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=False).first()
        if user is not None:
            try:
                send_verification_email(user)
            except Exception:  # pragma: no cover - falha de SMTP
                logger.exception("Falha ao reenviar verificação (user=%s).", user.pk)

        return Response(
            {"detail": VERIFICATION_RESENT}, status=status.HTTP_202_ACCEPTED
        )


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={202: MessageSerializer},
        description="Envia o link temporário de redefinição (resposta genérica).",
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is not None:
            try:
                send_password_reset_email(user)
            except Exception:  # pragma: no cover - falha de SMTP
                logger.exception("Falha ao enviar reset de senha (user=%s).", user.pk)

        return Response({"detail": RESET_REQUESTED}, status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={200: MessageSerializer},
        description=(
            "Define a nova senha e revoga todas as sessões (refresh tokens) "
            "anteriores do usuário."
        ),
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        revoked = blacklist_user_tokens(user)
        logger.info(
            "Senha redefinida (user=%s, tokens revogados=%s).", user.pk, revoked
        )

        return Response(
            {"detail": "Senha redefinida com sucesso. Faça login novamente."}
        )
