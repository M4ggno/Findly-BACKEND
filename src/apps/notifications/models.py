"""Modelos de notificação: inscrições de Web Push por usuário."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class PushSubscription(models.Model):
    """Inscrição de Web Push de um navegador/dispositivo.

    O front registra o objeto devolvido por ``PushManager.subscribe()``; o
    backend guarda os dados necessários para enviar a notificação e desativa a
    inscrição quando o provedor responde ``404``/``410`` (inscrição expirada).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
        verbose_name="usuário",
    )
    endpoint = models.URLField("endpoint", max_length=500, unique=True)
    p256dh = models.CharField("chave p256dh", max_length=200)
    auth = models.CharField("segredo auth", max_length=100)
    user_agent = models.CharField("user agent", max_length=255, blank=True)
    is_active = models.BooleanField("ativa", default=True)
    last_used_at = models.DateTimeField("último uso", null=True, blank=True)
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizada em", auto_now=True)

    class Meta:
        verbose_name = "inscrição de push"
        verbose_name_plural = "inscrições de push"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} — {self.endpoint[:48]}"

    def as_subscription_info(self) -> dict:
        """Formato aceito pelo ``pywebpush`` (mesmo do ``PushSubscription`` JS)."""
        return {
            "endpoint": self.endpoint,
            "keys": {"p256dh": self.p256dh, "auth": self.auth},
        }

    def mark_used(self) -> None:
        """Atualiza o último uso sem disparar ``updated_at`` em cascata."""
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at"])


__all__ = ["PushSubscription"]
