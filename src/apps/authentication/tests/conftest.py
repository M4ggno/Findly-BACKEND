"""Fixtures dos testes de autenticação.

Isola a suíte de dependências externas:
- cache em memória (não exige Redis);
- throttling desativado (os limites não são o alvo destes testes).
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _hermetic_settings(settings, monkeypatch):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

    # O DRF avalia ``DEFAULT_THROTTLE_RATES`` no import; em vez de mexer em
    # settings (referência compartilhada), neutralizamos o throttle nos testes.
    from rest_framework.throttling import ScopedRateThrottle

    monkeypatch.setattr(
        ScopedRateThrottle, "allow_request", lambda self, request, view: True
    )


@pytest.fixture
def active_user(db):
    from apps.users.models import User

    return User.objects.create_user(
        email="usuario@findly.local",
        password="S3nh@Forte!2026",
        full_name="Usuário Teste",
        phone="11999999999",
    )


@pytest.fixture
def inactive_user(db):
    from apps.users.models import User

    return User.objects.create_user(
        email="inativo@findly.local",
        password="S3nh@Forte!2026",
        full_name="Usuário Inativo",
        is_active=False,
    )
