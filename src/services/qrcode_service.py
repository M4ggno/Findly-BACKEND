"""Serviço de QR Code.

Usado para:

1. **Etiqueta de identificação** do item físico (contém o ``public_code``).
2. **Autorização de retirada** emitida na aprovação de um claim (token opaco,
   válido por 24 h e de uso único).

A geração devolve um ``ContentFile`` PNG pronto para ser salvo por um
``ImageField`` ou devolvido diretamente pela API.
"""

from __future__ import annotations

from io import BytesIO

import qrcode
from django.core.files.base import ContentFile
from qrcode.constants import ERROR_CORRECT_M

DEFAULT_BOX_SIZE = 10
DEFAULT_BORDER = 2


def build_qr_png(
    data: str,
    *,
    box_size: int = DEFAULT_BOX_SIZE,
    border: int = DEFAULT_BORDER,
) -> ContentFile:
    """Gera um QR Code PNG a partir de ``data``."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue(), name="qrcode.png")


def item_label_payload(item) -> str:
    """Conteúdo da etiqueta física: código público legível por qualquer leitor."""
    return f"FINDLY:{item.public_code}"


def withdrawal_payload(token: str) -> str:
    """Conteúdo do QR de retirada (token que a API valida na confirmação)."""
    return f"FINDLY:WITHDRAWAL:{token}"


def extract_withdrawal_token(value: str) -> str:
    """Aceita tanto o token puro quanto o conteúdo lido do QR Code."""
    value = (value or "").strip()
    prefix = "FINDLY:WITHDRAWAL:"
    if value.startswith(prefix):
        return value[len(prefix) :]
    return value
