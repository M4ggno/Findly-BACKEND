"""Views do app de usuários (perfil e gestão de contas).

Rotas montadas em ``/api/users/`` (ver ``urls.py``):

- ``GET/PUT/PATCH /api/users/me/`` — perfil do próprio usuário autenticado.
- ``GET /api/users/`` — listagem administrativa (busca, filtro e ordenação).
- ``GET /api/users/{id}/`` — detalhe administrativo.
- ``PUT/PATCH /api/users/{id}/`` — edição administrativa (papel/situação).
"""

from __future__ import annotations

import logging

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, mixins, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated

from .models import User
from .permissions import IsAdminRole
from .serializers import AdminUserUpdateSerializer, MeSerializer, UserSerializer

logger = logging.getLogger("findly.users")


@extend_schema_view(
    get=extend_schema(
        tags=["users"],
        summary="Consultar o próprio perfil",
        responses={200: MeSerializer},
    ),
    put=extend_schema(
        tags=["users"],
        summary="Atualizar o próprio perfil",
        request=MeSerializer,
        responses={200: MeSerializer},
    ),
    patch=extend_schema(
        tags=["users"],
        summary="Atualizar parcialmente o próprio perfil",
        request=MeSerializer,
        responses={200: MeSerializer},
    ),
)
class MeView(generics.RetrieveUpdateAPIView):
    """Perfil do usuário autenticado.

    O e-mail (identificador de login) e o papel são somente leitura. Para trocar
    a senha, use o fluxo de recuperação em ``/api/auth/password-reset/``.
    """

    serializer_class = MeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self) -> User:
        return self.request.user


@extend_schema_view(
    list=extend_schema(
        tags=["users"],
        summary="Listar usuários (administração)",
        responses={200: UserSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["users"],
        summary="Detalhar um usuário (administração)",
        responses={200: UserSerializer},
    ),
    update=extend_schema(
        tags=["users"],
        summary="Editar um usuário (administração)",
        request=AdminUserUpdateSerializer,
        responses={200: AdminUserUpdateSerializer},
    ),
    partial_update=extend_schema(
        tags=["users"],
        summary="Editar parcialmente um usuário (administração)",
        request=AdminUserUpdateSerializer,
        responses={200: AdminUserUpdateSerializer},
    ),
)
class UserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Gestão de contas — restrita a administradores.

    Não há criação por aqui: contas nascem pelo cadastro público
    (``/api/auth/register/``), com verificação de e-mail. Também não há exclusão:
    contas são **desativadas** (``is_active=False``), preservando o histórico de
    itens e a trilha de auditoria.
    """

    queryset = User.objects.all()
    permission_classes = [IsAdminRole]
    http_method_names = ["get", "put", "patch", "head", "options"]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["role", "is_active"]
    search_fields = ["email", "full_name", "phone"]
    ordering_fields = ["date_joined", "email", "full_name", "role"]
    ordering = ["-date_joined"]

    def get_serializer_class(self):
        if self.action in {"update", "partial_update"}:
            return AdminUserUpdateSerializer
        return UserSerializer

    def perform_update(self, serializer):
        user = serializer.save()

        # Conta desativada perde imediatamente as sessões: o token de acesso
        # deixa de autenticar (JWTAuthentication exige ``is_active``) e os
        # refresh tokens vão para a blacklist.
        if not user.is_active:
            from apps.authentication.services import blacklist_user_tokens

            try:
                revoked = blacklist_user_tokens(user)
            except Exception:  # pragma: no cover - falha de cache/DB não desfaz a ação
                logger.exception(
                    "Falha ao revogar tokens do usuário desativado (user=%s).", user.pk
                )
            else:
                logger.info(
                    "Usuário desativado (user=%s, tokens revogados=%s).",
                    user.pk,
                    revoked,
                )
