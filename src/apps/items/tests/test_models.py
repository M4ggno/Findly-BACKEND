"""Testes dos modelos do app de itens."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.items.models import FoundItem, ItemStatus


@pytest.mark.django_db
def test_public_code_is_generated_and_unique(common_user):
    now = timezone.now()
    first = FoundItem.objects.create(
        reported_by=common_user,
        title="Item A",
        description="Descrição A",
        found_at=now - timedelta(days=2),
        found_location="Local A",
    )
    second = FoundItem.objects.create(
        reported_by=common_user,
        title="Item B",
        description="Descrição B",
        found_at=now - timedelta(days=1),
        found_location="Local B",
    )

    assert len(first.public_code) == 10
    assert first.public_code.isalnum()
    assert first.public_code != second.public_code


@pytest.mark.django_db
def test_default_status_is_reported(found_item):
    assert found_item.status == ItemStatus.REPORTADO
    assert found_item.is_terminal is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    "terminal_status",
    [ItemStatus.DEVOLVIDO, ItemStatus.EXPIRADO, ItemStatus.ENCAMINHADO],
)
def test_terminal_statuses(found_item, terminal_status):
    found_item.status = terminal_status
    assert found_item.is_terminal is True


@pytest.mark.django_db
def test_str_contains_code_and_title(found_item):
    assert found_item.public_code in str(found_item)
    assert found_item.title in str(found_item)
