"""Fixtures dos testes de auditoria."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

PASSWORD = "S3nh@Forte!2026"


@pytest.fixture(autouse=True)
def _locmem_cache(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }


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
def found_payload():
    return {
        "title": "Mochila azul",
        "description": "Mochila com notebook e caderno.",
        "category": "eletronicos",
        "found_at": (timezone.now() - timedelta(hours=2)).isoformat(),
        "found_location": "Biblioteca central",
    }
