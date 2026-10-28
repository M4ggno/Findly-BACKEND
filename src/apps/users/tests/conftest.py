"""Fixtures dos testes do app de usuários.

Mantém a suíte independente de Redis (cache em memória) e expõe um client da DRF
com atalho para autenticação por usuário.
"""

from __future__ import annotations

import pytest
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
        phone="11999990001",
    )


@pytest.fixture
def other_user(db):
    from apps.users.models import User

    return User.objects.create_user(
        email="outro@findly.local",
        password=PASSWORD,
        full_name="Outro Usuário",
        phone="11999990002",
        role="operator",
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


@pytest.fixture
def superuser(db):
    from apps.users.models import User

    return User.objects.create_superuser(
        email="root@findly.local",
        password=PASSWORD,
        full_name="Superusuário",
    )


@pytest.fixture
def auth_client(api_client, common_user):
    """Client autenticado como usuário comum."""
    api_client.force_authenticate(user=common_user)
    return api_client
