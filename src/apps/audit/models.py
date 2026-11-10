"""Modelo da trilha de auditoria.

Cada evento registra **quem** fez **o quê** em **qual item** e **quando**. Os
registros são imutáveis: não há update nem delete pelo ORM (e o admin é somente
leitura). Isso atende ao requisito de rastreabilidade do README.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.items.models import FoundItem


class AuditAction(models.TextChoices):
    """Ações registradas na trilha (as de operações entram nas próximas etapas)."""

    CREATED = "CREATED", "Item cadastrado"
    STATUS_CHANGED = "STATUS_CHANGED", "Status alterado"
    CUSTODY_TRANSFERRED = "CUSTODY_TRANSFERRED", "Custódia transferida"
    CLAIM_APPROVED = "CLAIM_APPROVED", "Reivindicação aprovada"
    CLAIM_REJECTED = "CLAIM_REJECTED", "Reivindicação recusada"
    CLAIM_CANCELLED = "CLAIM_CANCELLED", "Reivindicação cancelada"
    WITHDRAWAL_CONFIRMED = "WITHDRAWAL_CONFIRMED", "Retirada confirmada"


class AuditEvent(models.Model):
    """Evento imutável da trilha de auditoria.

    ``responsible`` é anulável para permitir ações automáticas (ex.: expiração
    por tarefa agendada). Em ações humanas, é sempre preenchido.
    """

    item = models.ForeignKey(
        FoundItem,
        on_delete=models.PROTECT,
        related_name="audit_events",
        verbose_name="item",
    )
    action = models.CharField(
        "ação realizada",
        max_length=30,
        choices=AuditAction.choices,
        db_index=True,
    )
    previous_status = models.CharField(
        "status anterior",
        max_length=20,
        blank=True,
        help_text="Vazio quando o evento é a criação do item.",
    )
    new_status = models.CharField(
        "status novo",
        max_length=20,
        blank=True,
    )
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="audit_events",
        verbose_name="usuário responsável",
        null=True,
        blank=True,
    )
    collection_point = models.ForeignKey(
        "operations.CollectionPoint",
        on_delete=models.PROTECT,
        related_name="audit_events",
        verbose_name="ponto de coleta",
        null=True,
        blank=True,
        help_text="Preenchido quando o evento envolve um ponto de coleta.",
    )
    metadata = models.JSONField(
        "metadados",
        default=dict,
        blank=True,
        help_text="Contexto adicional (ex.: ponto de coleta, claim, QR).",
    )
    created_at = models.DateTimeField("timestamp", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "evento de auditoria"
        verbose_name_plural = "eventos de auditoria"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["item", "created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.item.public_code} — {self.get_action_display()}"

    def save(self, *args, **kwargs):
        """Permite apenas inserções; eventos existentes são imutáveis."""
        if not self._state.adding:
            raise ValueError(
                "Eventos de auditoria são imutáveis e não podem ser alterados."
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Impede a exclusão de eventos pelo ORM."""
        raise ValueError("Eventos de auditoria não podem ser excluídos.")
