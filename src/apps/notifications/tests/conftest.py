"""Fixtures dos testes do app de notificações."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.users.models import User

PASSWORD = "S3nh@Forte!2026"


@pytest.fixture(autouse=True)
def _hermetic_settings(settings):
    """Isola cache (throttle), e-mail e push do ambiente externo."""
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.NOTIFICATIONS_PUSH_ENABLED = False
    settings.NOTIFICATIONS_ASYNC_ENABLED = False


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        email="push@findly.local",
        password=PASSWORD,
        full_name="Usuário Push",
        is_active=True,
    )


@pytest.fixture
def other_user(db) -> User:
    return User.objects.create_user(
        email="outro-push@findly.local",
        password=PASSWORD,
        full_name="Outro Usuário",
        is_active=True,
    )


def make_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def auth_client(user: User) -> APIClient:
    return make_client(user)


@pytest.fixture
def other_client(other_user: User) -> APIClient:
    return make_client(other_user)
