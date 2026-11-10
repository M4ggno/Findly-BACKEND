"""Serializers da auditoria (somente leitura)."""

from __future__ import annotations

from rest_framework import serializers

from apps.items.models import FoundItem
from apps.users.models import User

from .models import AuditEvent


class AuditItemSerializer(serializers.ModelSerializer):
    """Referência mínima ao item auditado."""

    class Meta:
        model = FoundItem
        fields = ("id", "public_code", "title")
        read_only_fields = fields


class AuditUserSerializer(serializers.ModelSerializer):
    """Responsável pelo evento (sem dados sensíveis)."""

    class Meta:
        model = User
        fields = ("id", "full_name")
        read_only_fields = fields


class AuditEventSerializer(serializers.ModelSerializer):
    """Representação de um evento da trilha."""

    item = AuditItemSerializer(read_only=True)
    responsible = AuditUserSerializer(read_only=True)
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AuditEvent
        fields = (
            "id",
            "item",
            "action",
            "action_display",
            "previous_status",
            "new_status",
            "responsible",
            "metadata",
            "created_at",
        )
        read_only_fields = fields
