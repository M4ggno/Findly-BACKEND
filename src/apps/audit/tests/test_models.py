"""Testes do modelo e do serviço de auditoria."""

from __future__ import annotations

import pytest

from apps.audit.models import AuditAction, AuditEvent
from apps.audit.services import record_event
from apps.items.models import ItemStatus

pytestmark = pytest.mark.django_db


def test_record_event_persists_all_fields(found_item, operator_user):
    event = record_event(
        item=found_item,
        action=AuditAction.STATUS_CHANGED,
        user=operator_user,
        previous_status=ItemStatus.REPORTADO,
        new_status=ItemStatus.EM_CUSTODIA,
        metadata={"note": "recebido na portaria"},
    )

    assert event.pk is not None
    assert event.item == found_item
    assert event.action == AuditAction.STATUS_CHANGED
    assert event.previous_status == ItemStatus.REPORTADO
    assert event.new_status == ItemStatus.EM_CUSTODIA
    assert event.responsible == operator_user
    assert event.metadata == {"note": "recebido na portaria"}
    assert event.created_at is not None


def test_event_is_immutable(found_item, operator_user):
    event = record_event(
        item=found_item,
        action=AuditAction.CREATED,
        user=operator_user,
        new_status=ItemStatus.REPORTADO,
    )

    event.new_status = ItemStatus.DEVOLVIDO
    with pytest.raises(ValueError, match="imutáveis"):
        event.save()

    with pytest.raises(ValueError, match="não podem ser excluídos"):
        event.delete()

    event.refresh_from_db()
    assert event.new_status == ItemStatus.REPORTADO
    assert AuditEvent.objects.count() == 1


def test_events_are_ordered_newest_first(found_item, operator_user):
    first = record_event(
        item=found_item,
        action=AuditAction.CREATED,
        user=operator_user,
        new_status=ItemStatus.REPORTADO,
    )
    second = record_event(
        item=found_item,
        action=AuditAction.STATUS_CHANGED,
        user=operator_user,
        previous_status=ItemStatus.REPORTADO,
        new_status=ItemStatus.EM_CUSTODIA,
    )

    assert list(AuditEvent.objects.all()) == [second, first]


def test_str_contains_item_and_action(found_item, operator_user):
    event = record_event(
        item=found_item,
        action=AuditAction.CREATED,
        user=operator_user,
        new_status=ItemStatus.REPORTADO,
    )

    assert found_item.public_code in str(event)
    assert "Item cadastrado" in str(event)
