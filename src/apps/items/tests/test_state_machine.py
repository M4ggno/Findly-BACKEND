"""Testes da máquina de estados do item encontrado."""

from __future__ import annotations

import pytest

from apps.items.models import FoundItem, ItemStatus
from apps.items.services import (
    InvalidStatusTransition,
    allowed_next_statuses,
    transition_found_item,
)


@pytest.mark.django_db
def test_full_happy_path(found_item):
    for target in (
        ItemStatus.EM_CUSTODIA,
        ItemStatus.AGUARDANDO_RETIRADA,
        ItemStatus.DEVOLVIDO,
    ):
        found_item = transition_found_item(found_item, target)

    assert found_item.status == ItemStatus.DEVOLVIDO
    assert found_item.is_terminal is True
    assert FoundItem.objects.get(pk=found_item.pk).status == ItemStatus.DEVOLVIDO


@pytest.mark.django_db
def test_forwarding_from_reported(found_item):
    found_item = transition_found_item(found_item, ItemStatus.ENCAMINHADO)
    assert found_item.status == ItemStatus.ENCAMINHADO


@pytest.mark.django_db
def test_invalid_jump_is_rejected(found_item):
    with pytest.raises(InvalidStatusTransition):
        transition_found_item(found_item, ItemStatus.DEVOLVIDO)

    found_item.refresh_from_db()
    assert found_item.status == ItemStatus.REPORTADO


@pytest.mark.django_db
def test_same_status_is_rejected(found_item):
    with pytest.raises(InvalidStatusTransition):
        transition_found_item(found_item, ItemStatus.REPORTADO)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "terminal_status",
    [ItemStatus.DEVOLVIDO, ItemStatus.EXPIRADO, ItemStatus.ENCAMINHADO],
)
def test_terminal_states_have_no_next_status(found_item, terminal_status):
    found_item.status = terminal_status
    found_item.save(update_fields=["status"])

    assert allowed_next_statuses(terminal_status) == frozenset()
    with pytest.raises(InvalidStatusTransition):
        transition_found_item(found_item, ItemStatus.REPORTADO)
