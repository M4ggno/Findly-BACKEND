"""Modelos do app de itens: achados, perdidos e fotos.

Um **achado** (``FoundItem``) é um objeto encontrado e cadastrado por um usuário
ou operador. Um **perdido** (``LostReport``) é um alerta aberto por quem procura
um pertence. O ciclo de vida do achado é controlado pela máquina de estados em
``services.py`` — o campo ``status`` nunca deve ser alterado diretamente pelas
views.
"""

from __future__ import annotations

import secrets
import uuid
from pathlib import Path

from django.conf import settings
from django.db import models

# Alfabeto sem caracteres ambíguos (0/O, 1/I) para códigos lidos em etiquetas.
PUBLIC_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
PUBLIC_CODE_LENGTH = 10


def generate_public_code() -> str:
    """Gera o código público usado em URLs, etiquetas e QR Codes."""
    return "".join(
        secrets.choice(PUBLIC_CODE_ALPHABET) for _ in range(PUBLIC_CODE_LENGTH)
    )


def item_photo_upload_to(instance: ItemPhoto, filename: str) -> str:
    """Organiza as fotos por item: ``items/<codigo>/<uuid>.jpg``."""
    suffix = Path(filename).suffix.lower() or ".jpg"
    return f"items/{instance.item.public_code}/{uuid.uuid4().hex}{suffix}"


class Category(models.TextChoices):
    """Categorias usadas em achados e perdidos (filtro e match)."""

    ELETRONICOS = "eletronicos", "Eletrônicos"
    DOCUMENTOS = "documentos", "Documentos"
    VESTUARIO = "vestuario", "Vestuário e acessórios"
    CHAVES = "chaves", "Chaves"
    CARTEIRAS = "carteiras", "Carteiras e bolsas"
    MOVEIS = "moveis", "Móveis e utensílios"
    OUTROS = "outros", "Outros"


class ItemStatus(models.TextChoices):
    """Máquina de estados do achado (README, seção 3.2)."""

    REPORTADO = "REPORTADO", "Reportado"
    EM_CUSTODIA = "EM_CUSTODIA", "Em custódia"
    AGUARDANDO_RETIRADA = "AGUARDANDO_RETIRADA", "Aguardando retirada"
    DEVOLVIDO = "DEVOLVIDO", "Devolvido"
    EXPIRADO = "EXPIRADO", "Expirado"
    ENCAMINHADO = "ENCAMINHADO", "Encaminhado"


class LostReportStatus(models.TextChoices):
    """Situação de um alerta de item perdido."""

    ABERTO = "ABERTO", "Aberto"
    ENCONTRADO = "ENCONTRADO", "Encontrado"
    CANCELADO = "CANCELADO", "Cancelado"
    EXPIRADO = "EXPIRADO", "Expirado"


class FoundItem(models.Model):
    """Objeto encontrado e registrado na plataforma."""

    public_code = models.CharField(
        "código público",
        max_length=PUBLIC_CODE_LENGTH,
        unique=True,
        default=generate_public_code,
        editable=False,
        db_index=True,
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="found_items",
        verbose_name="reportado por",
    )
    title = models.CharField("título", max_length=120)
    description = models.TextField("descrição")
    category = models.CharField(
        "categoria",
        max_length=30,
        choices=Category.choices,
        default=Category.OUTROS,
        db_index=True,
    )
    found_at = models.DateTimeField("encontrado em")
    found_location = models.CharField("local do achado", max_length=255)
    status = models.CharField(
        "status",
        max_length=20,
        choices=ItemStatus.choices,
        default=ItemStatus.REPORTADO,
        db_index=True,
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        verbose_name = "item encontrado"
        verbose_name_plural = "itens encontrados"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "category"]),
            models.Index(fields=["found_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.public_code} — {self.title}"

    @property
    def is_terminal(self) -> bool:
        """``True`` quando o item não pode mais mudar de estado."""
        return self.status in {
            ItemStatus.DEVOLVIDO,
            ItemStatus.EXPIRADO,
            ItemStatus.ENCAMINHADO,
        }


class LostReport(models.Model):
    """Alerta aberto por quem procura um pertence."""

    public_code = models.CharField(
        "código público",
        max_length=PUBLIC_CODE_LENGTH,
        unique=True,
        default=generate_public_code,
        editable=False,
        db_index=True,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="lost_reports",
        verbose_name="dono",
    )
    title = models.CharField("título", max_length=120)
    description = models.TextField("descrição")
    category = models.CharField(
        "categoria",
        max_length=30,
        choices=Category.choices,
        default=Category.OUTROS,
        db_index=True,
    )
    lost_at = models.DateTimeField("perdido em")
    lost_location = models.CharField("local da perda", max_length=255)
    contact_note = models.CharField(
        "observação de contato",
        max_length=255,
        blank=True,
        help_text="Ex.: 'Falar com a portaria do prédio'.",
    )
    status = models.CharField(
        "status",
        max_length=20,
        choices=LostReportStatus.choices,
        default=LostReportStatus.ABERTO,
        db_index=True,
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        verbose_name = "item perdido"
        verbose_name_plural = "itens perdidos"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "category"]),
            models.Index(fields=["lost_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.public_code} — {self.title}"


class ItemPhoto(models.Model):
    """Foto de um item encontrado (já processada pelo serviço de fotos)."""

    item = models.ForeignKey(
        FoundItem,
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name="item",
    )
    image = models.ImageField("imagem", upload_to=item_photo_upload_to)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_item_photos",
        verbose_name="enviada por",
    )
    created_at = models.DateTimeField("criada em", auto_now_add=True)

    class Meta:
        verbose_name = "foto do item"
        verbose_name_plural = "fotos do item"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Foto de {self.item.public_code} (#{self.pk})"
