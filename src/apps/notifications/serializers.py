"""Serializers das inscrições de push (formato Web Push)."""

from __future__ import annotations

from rest_framework import serializers

from .models import PushSubscription


class PushKeysSerializer(serializers.Serializer):
    """Par de chaves gerado pelo ``PushManager.subscribe()``."""

    p256dh = serializers.CharField(max_length=200)
    auth = serializers.CharField(max_length=100)


class PushSubscriptionSerializer(serializers.ModelSerializer):
    """Cria/atualiza a inscrição do usuário autenticado.

    O corpo segue o padrão do navegador::

        {
          "endpoint": "https://fcm.googleapis.com/fcm/send/...",
          "keys": {"p256dh": "...", "auth": "..."},
          "user_agent": "Mozilla/5.0 ..."
        }

    O mesmo ``endpoint`` pode ser reenviado com segurança: a inscrição é
    atualizada (inclusive quando outro usuário entra no mesmo navegador).
    """

    keys = PushKeysSerializer(write_only=True)

    class Meta:
        model = PushSubscription
        fields = (
            "id",
            "endpoint",
            "keys",
            "user_agent",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "is_active", "created_at", "updated_at")
        # A unicidade do endpoint é tratada no create; não queremos o validador
        # padrão revelando que o endpoint já existe para outro usuário.
        extra_kwargs = {"endpoint": {"validators": []}}

    def create(self, validated_data):
        keys = validated_data.pop("keys")
        endpoint = validated_data.pop("endpoint")
        user = self.context["request"].user

        subscription, _ = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user": user,
                "p256dh": keys["p256dh"],
                "auth": keys["auth"],
                **validated_data,
            },
        )
        return subscription

    def to_representation(self, instance: PushSubscription) -> dict:
        data = super().to_representation(instance)
        data["keys"] = {"p256dh": instance.p256dh, "auth": instance.auth}
        return data


__all__ = ["PushKeysSerializer", "PushSubscriptionSerializer"]
