"""Serializers do app de usuários.

Por enquanto expõe apenas a representação pública (somente leitura), reutilizada
pelo app ``authentication`` na resposta do login. Os serializers de perfil e de
gestão entram na etapa seguinte.
"""

from __future__ import annotations

from rest_framework import serializers

from .models import User


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
