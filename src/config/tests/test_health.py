"""Testes dos healthchecks."""

from __future__ import annotations

import pytest
from django.test import override_settings
from django.urls import reverse

from config import health

pytestmark = pytest.mark.django_db

LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


def test_liveness_is_public_and_does_not_touch_dependencies(client, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("liveness não deve consultar dependências")

    monkeypatch.setattr(health, "_database_ok", boom)
    monkeypatch.setattr(health, "_cache_ok", boom)

    response = client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@override_settings(CACHES=LOCMEM_CACHE)
def test_readiness_reports_healthy_dependencies(client):
    response = client.get(reverse("health-ready"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "cache": "ok"}


@override_settings(CACHES=LOCMEM_CACHE)
def test_readiness_returns_503_when_database_is_down(client, monkeypatch):
    monkeypatch.setattr(health, "_database_ok", lambda: False)

    response = client.get(reverse("health-ready"))

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "database": "down",
        "cache": "ok",
    }


@override_settings(CACHES=LOCMEM_CACHE)
def test_readiness_returns_503_when_cache_is_down(client, monkeypatch):
    monkeypatch.setattr(health, "_cache_ok", lambda: False)

    response = client.get(reverse("health-ready"))

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "database": "ok",
        "cache": "down",
    }
