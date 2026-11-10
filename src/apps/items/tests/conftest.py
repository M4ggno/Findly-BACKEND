"""Fixtures dos testes do app de itens.

Mantém a suíte hermética: cache em memória, ``MEDIA_ROOT`` temporário e
fábricas de usuários/itens/imagens.
"""

from __future__ import annotations

from datetime import timedelta
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

PASSWORD = "S3nh@Forte!2026"


@pytest.fixture(autouse=True)
def _hermetic_settings(settings, tmp_path):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.NOTIFICATIONS_PUSH_ENABLED = False


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def common_user(db):
    from apps.users.models import User

    return User.objects.create_user(
        email="comum@findly.local",
        password=PASSWORD,
        full_name="Usuário Comum",
        phone="11999990001",
    )


@pytest.fixture
def other_user(db):
    from apps.users.models import User

    return User.objects.create_user(
        email="outro@findly.local",
        password=PASSWORD,
        full_name="Outro Usuário",
    )


@pytest.fixture
def operator_user(db):
    from apps.users.models import User

    return User.objects.create_user(
        email="operador@findly.local",
        password=PASSWORD,
        full_name="Operador de Ponto",
        role="operator",
    )


@pytest.fixture
def admin_user(db):
    from apps.users.models import User

    return User.objects.create_user(
        email="admin@findly.local",
        password=PASSWORD,
        full_name="Administrador",
        role="admin",
        is_staff=True,
    )


def _client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def auth_client(common_user) -> APIClient:
    return _client_for(common_user)


@pytest.fixture
def other_client(other_user) -> APIClient:
    return _client_for(other_user)


@pytest.fixture
def operator_client(operator_user) -> APIClient:
    return _client_for(operator_user)


@pytest.fixture
def admin_client(admin_user) -> APIClient:
    return _client_for(admin_user)


@pytest.fixture
def found_item(db, common_user):
    from apps.items.models import Category, FoundItem

    return FoundItem.objects.create(
        reported_by=common_user,
        title="Carteira preta",
        description="Carteira de couro com documentos.",
        category=Category.CARTEIRAS,
        found_at=timezone.now() - timedelta(days=1),
        found_location="Recepção do prédio A",
    )


@pytest.fixture
def lost_report(db, common_user):
    from apps.items.models import Category, LostReport

    return LostReport.objects.create(
        owner=common_user,
        title="Chaves do carro",
        description="Chave com controle remoto e chaveiro azul.",
        category=Category.CHAVES,
        lost_at=timezone.now() - timedelta(hours=4),
        lost_location="Estacionamento do shopping",
    )


@pytest.fixture
def photo_upload():
    """Fábrica de uploads de imagem para os testes de fotos."""

    def _make(
        name: str = "foto.jpg",
        size: tuple[int, int] = (80, 60),
        with_exif: bool = False,
        content_type: str = "image/jpeg",
    ) -> SimpleUploadedFile:
        buffer = BytesIO()
        image = Image.new("RGB", size, (200, 120, 40))
        kwargs = {}
        if with_exif:
            exif = Image.Exif()
            exif[0x0112] = 6  # Orientation (rotação de 90°)
            kwargs["exif"] = exif
        image.save(buffer, format="JPEG", **kwargs)
        return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)

    return _make


@pytest.fixture
def found_payload():
    return {
        "title": "Mochila azul",
        "description": "Mochila com notebook e caderno.",
        "category": "eletronicos",
        "found_at": (timezone.now() - timedelta(hours=2)).isoformat(),
        "found_location": "Biblioteca central",
    }


@pytest.fixture
def lost_payload():
    return {
        "title": "Óculos de grau",
        "description": "Armação dourada, lentes transparentes.",
        "category": "outros",
        "lost_at": (timezone.now() - timedelta(hours=6)).isoformat(),
        "lost_location": "Praça de alimentação",
        "contact_note": "Falar na portaria do prédio.",
    }
