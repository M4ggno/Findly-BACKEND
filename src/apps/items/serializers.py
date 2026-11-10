"""Serializers do app de itens.

Separação leitura/escrita:

- ``FoundItemSerializer`` / ``LostReportSerializer``: representação pública
  (inclui ``public_code``, status e fotos).
- ``*WriteSerializer``: campos editáveis. ``to_representation`` devolve a versão
  completa, para que ``POST``/``PATCH`` já retornem o recurso atualizado.
- ``ItemPhotoUploadSerializer``: recebe o multipart e delega o processamento ao
  ``services.photo_service``.
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from apps.users.models import User
from services.photo_service import PhotoValidationError, process_upload, validate_upload

from .models import (
    Category,
    FoundItem,
    ItemPhoto,
    ItemStatus,
    LostReport,
    LostReportStatus,
)

# Tolera pequenos desvios de relógio entre cliente e servidor.
FUTURE_TOLERANCE = timedelta(minutes=5)


class ReporterSerializer(serializers.ModelSerializer):
    """Dados públicos de quem cadastrou (sem e-mail/telefone)."""

    class Meta:
        model = User
        fields = ("id", "full_name")
        read_only_fields = fields


class ItemPhotoSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ItemPhoto
        fields = ("id", "image", "uploaded_by", "created_at")
        read_only_fields = fields


class FoundItemSerializer(serializers.ModelSerializer):
    """Representação completa de um achado."""

    reported_by = ReporterSerializer(read_only=True)
    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    photos = ItemPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = FoundItem
        fields = (
            "id",
            "public_code",
            "reported_by",
            "title",
            "description",
            "category",
            "category_display",
            "found_at",
            "found_location",
            "status",
            "status_display",
            "photos",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class FoundItemWriteSerializer(serializers.ModelSerializer):
    """Criação/edição de achados (autor, operador ou admin)."""

    class Meta:
        model = FoundItem
        fields = ("title", "description", "category", "found_at", "found_location")

    def validate_found_at(self, value):
        if value > timezone.now() + FUTURE_TOLERANCE:
            raise serializers.ValidationError(
                "A data do achado não pode estar no futuro."
            )
        return value

    def to_representation(self, instance):
        return FoundItemSerializer(instance, context=self.context).data


class FoundItemStatusSerializer(serializers.Serializer):
    """Corpo de ``POST /api/items/found/{code}/status/``."""

    status = serializers.ChoiceField(choices=ItemStatus.choices)


class LostReportSerializer(serializers.ModelSerializer):
    """Representação completa de um alerta de perda."""

    owner = ReporterSerializer(read_only=True)
    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = LostReport
        fields = (
            "id",
            "public_code",
            "owner",
            "title",
            "description",
            "category",
            "category_display",
            "lost_at",
            "lost_location",
            "contact_note",
            "status",
            "status_display",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class LostReportWriteSerializer(serializers.ModelSerializer):
    """Criação/edição de alertas de perda."""

    class Meta:
        model = LostReport
        fields = (
            "title",
            "description",
            "category",
            "lost_at",
            "lost_location",
            "contact_note",
        )

    def validate_lost_at(self, value):
        if value > timezone.now() + FUTURE_TOLERANCE:
            raise serializers.ValidationError(
                "A data da perda não pode estar no futuro."
            )
        return value

    def to_representation(self, instance):
        return LostReportSerializer(instance, context=self.context).data


class ItemPhotoUploadSerializer(serializers.Serializer):
    """Upload de uma foto (multipart/form-data)."""

    image = serializers.ImageField()

    def validate_image(self, value):
        try:
            validate_upload(value)
        except PhotoValidationError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value

    def create(self, validated_data):
        item: FoundItem = self.context["item"]
        request = self.context["request"]
        processed = process_upload(validated_data["image"])
        return ItemPhoto.objects.create(
            item=item,
            image=processed,
            uploaded_by=request.user,
        )


__all__ = [
    "Category",
    "FoundItemSerializer",
    "FoundItemStatusSerializer",
    "FoundItemWriteSerializer",
    "ItemPhotoSerializer",
    "ItemPhotoUploadSerializer",
    "LostReportSerializer",
    "LostReportStatus",
    "LostReportWriteSerializer",
    "ReporterSerializer",
]
