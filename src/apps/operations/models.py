"""Modelos do app de operações.

O fluxo de custódia/retirada é sempre conduzido por ``operations/services.py``;
as views não alteram ``status``, custódia ou claims diretamente.

- ``CollectionPoint``: unidade física autorizada a guardar itens.
- ``CustodyRecord``: quem detém a posse física do item em cada período.
- ``Claim``: reivindicação de propriedade feita por um usuário.
- ``WithdrawalAuthority``: QR Code temporário (24 h) e de uso único emitido na
  aprovação de um claim.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.items.models import FoundItem

# Validade do QR Code de retirada (README, seção 3.4).
WITHDRAWAL_TTL = timedelta(hours=24)
WITHDRAWAL_TOKEN_BYTES = 32


def generate_withdrawal_token() -> str:
    """Gera um token opaco, URL-safe e imprevisível para a retirada."""
    return secrets.token_urlsafe(WITHDRAWAL_TOKEN_BYTES)


def withdrawal_qr_upload_to(instance: WithdrawalAuthority, filename: str) -> str:
    """Organiza os QR Codes de retirada em ``qrcodes/withdrawals/<token>.png``."""
    return f"qrcodes/withdrawals/{instance.token}.png"


class CollectionPoint(models.Model):
    """Ponto de coleta autorizado a receber itens encontrados."""

    name = models.CharField("nome", max_length=120)
    address = models.CharField("endereço", max_length=255)
    opening_hours = models.CharField(
        "horário de funcionamento",
        max_length=120,
        blank=True,
        help_text="Ex.: 'Seg a Sex, 08:00–18:00'.",
    )
    capacity = models.PositiveIntegerField(
        "capacidade",
        null=True,
        blank=True,
        help_text="Máximo de itens em custódia; vazio significa ilimitado.",
    )
    operators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="collection_points",
        verbose_name="operadores responsáveis",
        blank=True,
    )
    is_active = models.BooleanField("ativo", default=True, db_index=True)
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        verbose_name = "ponto de coleta"
        verbose_name_plural = "pontos de coleta"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def current_occupancy(self) -> int:
        """Itens atualmente em custódia neste ponto."""
        return self.custody_records.filter(ended_at__isnull=True).count()

    @property
    def has_capacity(self) -> bool:
        """``False`` quando a capacidade configurada já foi atingida."""
        if self.capacity is None:
            return True
        return self.current_occupancy < self.capacity


class CustodyRecord(models.Model):
    """Período em que um usuário ou ponto de coleta detém o item.

    Exatamente um detentor é preenchido por registro e cada item tem no máximo
    um registro aberto (``ended_at`` nulo).
    """

    item = models.ForeignKey(
        FoundItem,
        on_delete=models.PROTECT,
        related_name="custody_records",
        verbose_name="item",
    )
    held_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="custody_records",
        verbose_name="detido por (usuário)",
        null=True,
        blank=True,
    )
    collection_point = models.ForeignKey(
        CollectionPoint,
        on_delete=models.PROTECT,
        related_name="custody_records",
        verbose_name="detido por (ponto de coleta)",
        null=True,
        blank=True,
    )
    note = models.CharField("observação", max_length=255, blank=True)
    started_at = models.DateTimeField("início", default=timezone.now, db_index=True)
    ended_at = models.DateTimeField("fim", null=True, blank=True, db_index=True)
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "registro de custódia"
        verbose_name_plural = "registros de custódia"
        ordering = ["-started_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(collection_point__isnull=False)
                | Q(held_by_user__isnull=False),
                name="custody_has_a_holder",
            ),
            models.UniqueConstraint(
                fields=["item"],
                condition=Q(ended_at__isnull=True),
                name="custody_one_active_per_item",
            ),
        ]

    def __str__(self) -> str:
        holder = self.collection_point or self.held_by_user
        return f"{self.item.public_code} — {holder}"

    @property
    def is_active(self) -> bool:
        return self.ended_at is None


class ClaimStatus(models.TextChoices):
    """Situação de uma reivindicação de propriedade."""

    PENDING = "PENDING", "Pendente"
    APPROVED = "APPROVED", "Aprovada"
    REJECTED = "REJECTED", "Recusada"
    CANCELLED = "CANCELLED", "Cancelada"


class Claim(models.Model):
    """Reivindicação feita por alguém que diz ser dono do item."""

    item = models.ForeignKey(
        FoundItem,
        on_delete=models.PROTECT,
        related_name="claims",
        verbose_name="item",
    )
    claimant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="claims",
        verbose_name="reivindicante",
    )
    status = models.CharField(
        "situação",
        max_length=20,
        choices=ClaimStatus.choices,
        default=ClaimStatus.PENDING,
        db_index=True,
    )
    message = models.TextField(
        "mensagem",
        blank=True,
        help_text="Descrição de características que comprovem a propriedade.",
    )
    decision_note = models.TextField("justificativa da decisão", blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_claims",
        verbose_name="avaliada por",
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField("avaliada em", null=True, blank=True)
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizada em", auto_now=True)

    class Meta:
        verbose_name = "reivindicação"
        verbose_name_plural = "reivindicações"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["item", "claimant"],
                condition=Q(status="PENDING"),
                name="claim_one_pending_per_user_item",
            ),
            models.UniqueConstraint(
                fields=["item"],
                condition=Q(status="APPROVED"),
                name="claim_one_approved_per_item",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.item.public_code} — {self.claimant} ({self.get_status_display()})"
        )

    @property
    def can_be_reviewed(self) -> bool:
        return self.status == ClaimStatus.PENDING


class WithdrawalAuthority(models.Model):
    """Autorização temporária de retirada emitida ao aprovar um claim.

    O token é opaco, expira em ``WITHDRAWAL_TTL`` e só pode ser usado uma vez.
    """

    claim = models.OneToOneField(
        Claim,
        on_delete=models.PROTECT,
        related_name="withdrawal",
        verbose_name="reivindicação",
    )
    token = models.CharField(
        "token",
        max_length=64,
        unique=True,
        default=generate_withdrawal_token,
        editable=False,
    )
    qr_image = models.ImageField(
        "QR Code",
        upload_to=withdrawal_qr_upload_to,
        blank=True,
    )
    expires_at = models.DateTimeField("expira em", db_index=True)
    used_at = models.DateTimeField("usado em", null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="issued_withdrawals",
        verbose_name="emitido por",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "autorização de retirada"
        verbose_name_plural = "autorizações de retirada"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"Retirada de {self.claim.item.public_code}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_valid(self) -> bool:
        return self.used_at is None and not self.is_expired
