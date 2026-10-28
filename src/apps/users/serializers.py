"""Serializers do app de usuários.

- ``UserSerializer``: representação pública (leitura), reutilizada na resposta do
  login e nas listagens administrativas.
- ``MeSerializer``: perfil do próprio usuário (leitura + edição dos dados
  cadastrais).
- ``AdminUserUpdateSerializer``: edição administrativa (papel e situação da
  conta).
"""

from __future__ import annotations

from rest_framework import serializers

from .models import Role, User


class UserSerializer(serializers.ModelSerializer):
    """Dados públicos do usuário (sem campos sensíveis)."""

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "phone",
            "role",
            "is_active",
            "date_joined",
        )
        read_only_fields = fields


class MeSerializer(serializers.ModelSerializer):
    """Perfil do usuário autenticado.

    Só ``full_name`` e ``phone`` são editáveis: o e-mail é o identificador de
    login (trocá-lo exigiria um novo ciclo de verificação) e ``role`` /
    ``is_active`` são controlados pela administração.
    """

    class Meta:
        model = User
        fields = UserSerializer.Meta.fields
        read_only_fields = (
            "id",
            "email",
            "role",
            "is_active",
            "date_joined",
        )


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Edição administrativa de uma conta.

    O administrador pode corrigir os dados cadastrais, promover/rebaixar o papel
    e (des)ativar a conta. A edição do próprio registro é bloqueada: o admin usa
    ``/api/users/me/`` para os próprios dados, o que evita rebaixar ou desativar
    a si mesmo por engano.
    """

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "phone",
            "role",
            "is_active",
            "is_staff",
            "date_joined",
            "last_login",
        )
        read_only_fields = (
            "id",
            "email",
            "is_staff",
            "date_joined",
            "last_login",
        )

    def validate(self, attrs: dict) -> dict:
        request = self.context["request"]

        if self.instance == request.user:
            raise serializers.ValidationError(
                "Use /api/users/me/ para alterar seus próprios dados."
            )

        if (
            self.instance.is_superuser
            and "role" in attrs
            and attrs["role"] != Role.ADMIN
        ):
            raise serializers.ValidationError(
                {"role": "Um superusuário não pode perder o papel de administrador."}
            )

        return attrs
