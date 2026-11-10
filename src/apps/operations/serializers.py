"""Serializers do app de operações."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.items.models import FoundItem
from apps.users.models import User

from .models import (
    Claim,
    CollectionPoint,
    CustodyRecord,
    WithdrawalAuthority,
)


class ItemRefSerializer(serializers.ModelSerializer):
    """Referência mínima ao item."""

    class Meta:
        model = FoundItem
        fields = ("id", "public_code", "title")
        read_only_fields = fields


class UserRefSerializer(serializers.ModelSerializer):
    """Referência mínima ao usuário (sem e-mail/telefone)."""

    class Meta:
        model = User
        fields = ("id", "full_name")
        read_only_fields = fields


class PointRefSerializer(serializers.ModelSerializer):
    """Referência mínima ao ponto de coleta."""

    class Meta:
        model = CollectionPoint
        fields = ("id", "name", "address")
        read_only_fields = fields


class CollectionPointSerializer(serializers.ModelSerializer):
    """Ponto de coleta: leitura completa e escrita administrativa."""

    operators = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        required=False,
    )
    operators_display = UserRefSerializer(source="operators", many=True, read_only=True)
    occupancy = serializers.IntegerField(source="current_occupancy", read_only=True)
    has_capacity = serializers.BooleanField(read_only=True)

    class Meta:
        model = CollectionPoint
        fields = (
            "id",
            "name",
            "address",
            "opening_hours",
            "capacity",
            "is_active",
            "operators",
            "operators_display",
            "occupancy",
            "has_capacity",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_operators(self, value):
        invalid = [
            user.email for user in value if not (user.is_operator or user.is_admin)
        ]
        if invalid:
            raise serializers.ValidationError(
                "Apenas operadores ou administradores podem ser responsáveis: "
                + ", ".join(invalid)
            )
        return value


class CustodyRecordSerializer(serializers.ModelSerializer):
    """Registro de custódia (somente leitura)."""

    item = ItemRefSerializer(read_only=True)
    held_by_user = UserRefSerializer(read_only=True)
    collection_point = PointRefSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = CustodyRecord
        fields = (
            "id",
            "item",
            "held_by_user",
            "collection_point",
            "note",
            "started_at",
            "ended_at",
            "is_active",
            "created_at",
        )
        read_only_fields = fields


class CustodyTransferSerializer(serializers.Serializer):
    """Corpo de ``POST .../custody/transfer/``."""

    collection_point = serializers.PrimaryKeyRelatedField(
        queryset=CollectionPoint.objects.filter(is_active=True)
    )
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)


class WithdrawalSerializer(serializers.ModelSerializer):
    """Autorização de retirada exposta ao reivindicante/operador."""

    is_valid = serializers.BooleanField(read_only=True)
    qr_image = serializers.SerializerMethodField()

    class Meta:
        model = WithdrawalAuthority
        fields = (
            "id",
            "token",
            "expires_at",
            "used_at",
            "is_valid",
            "qr_image",
            "created_at",
        )
        read_only_fields = fields

    def get_qr_image(self, obj: WithdrawalAuthority) -> str | None:
        if not obj.qr_image:
            return None
        request = self.context.get("request")
        url = obj.qr_image.url
        return request.build_absolute_uri(url) if request else url


class ClaimSerializer(serializers.ModelSerializer):
    """Representação completa de um claim."""

    item = ItemRefSerializer(read_only=True)
    claimant = UserRefSerializer(read_only=True)
    reviewed_by = UserRefSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    withdrawal = serializers.SerializerMethodField()

    class Meta:
        model = Claim
        fields = (
            "id",
            "item",
            "claimant",
            "status",
            "status_display",
            "message",
            "decision_note",
            "reviewed_by",
            "reviewed_at",
            "withdrawal",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    @extend_schema_field(WithdrawalSerializer)
    def get_withdrawal(self, obj: Claim):
        authority = getattr(obj, "withdrawal", None)
        if authority is None:
            return None
        return WithdrawalSerializer(
            authority, context={"request": self.context.get("request")}
        ).data


class ClaimCreateSerializer(serializers.Serializer):
    """Corpo de ``POST /api/operations/items/found/{code}/claims/``."""

    message = serializers.CharField(required=False, allow_blank=True)


class ClaimDecisionSerializer(serializers.Serializer):
    """Corpo de aprovação/recusa de um claim."""

    decision_note = serializers.CharField(required=False, allow_blank=True)


class WithdrawalConfirmSerializer(serializers.Serializer):
    """Corpo de ``POST /api/operations/withdrawals/confirm/``."""

    token = serializers.CharField(max_length=255)
