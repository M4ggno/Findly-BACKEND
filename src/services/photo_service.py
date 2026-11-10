"""Serviço de fotos dos itens.

Responsabilidades:

1. Validar extensão e tamanho do arquivo enviado.
2. Corrigir a orientação via ``ImageOps.exif_transpose``.
3. Redimensionar para no máximo ``MAX_DIMENSION`` (mantendo proporção).
4. Recomprimir em JPEG, **sem metadados EXIF** (geolocalização, câmera etc.).

O arquivo processado é devolvido como ``ContentFile`` e salvo pelo campo
``ItemPhoto.image``.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import uuid4

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_DIMENSION = 1600  # px (maior lado)
JPEG_QUALITY = 85
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class PhotoValidationError(ValueError):
    """Erro de validação de uma foto enviada pelo cliente."""


def _extension(uploaded_file) -> str:
    return Path(getattr(uploaded_file, "name", "")).suffix.lower()


def validate_upload(uploaded_file) -> None:
    """Valida extensão, tamanho e se o conteúdo é realmente uma imagem."""
    if _extension(uploaded_file) not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise PhotoValidationError(
            f"Formato não suportado. Envie um arquivo {allowed}."
        )

    size = getattr(uploaded_file, "size", 0) or 0
    if size > MAX_UPLOAD_BYTES:
        limit_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        raise PhotoValidationError(f"A imagem deve ter no máximo {limit_mb} MB.")

    try:
        uploaded_file.seek(0)
        with Image.open(uploaded_file) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise PhotoValidationError(
            "O arquivo enviado não é uma imagem válida."
        ) from exc
    except Image.DecompressionBombError as exc:  # pragma: no cover - defesa
        raise PhotoValidationError("Imagem grande demais para processamento.") from exc
    finally:
        uploaded_file.seek(0)


def process_upload(uploaded_file) -> ContentFile:
    """Valida, normaliza e devolve a imagem recompilada em JPEG."""
    validate_upload(uploaded_file)
    uploaded_file.seek(0)

    try:
        with Image.open(uploaded_file) as image:
            # Aplica a orientação do EXIF *antes* de descartar os metadados.
            image = ImageOps.exif_transpose(image)

            if image.mode in {"RGBA", "LA", "P"}:
                # Fundo branco para preservar transparência sem alpha no JPEG.
                rgba = image.convert("RGBA")
                background = Image.new("RGB", rgba.size, (255, 255, 255))
                background.paste(rgba, mask=rgba.split()[-1])
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")

            image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

            buffer = BytesIO()
            # Salvar sem ``exif=`` grava o JPEG sem os metadados originais.
            image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise PhotoValidationError("Não foi possível processar a imagem.") from exc

    return ContentFile(buffer.getvalue(), name=f"{uuid4().hex}.jpg")
