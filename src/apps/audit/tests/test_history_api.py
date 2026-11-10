"""Testes do histórico de auditoria aninhado ao item."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.audit.models import AuditAction
from apps.audit.services import record_event
from apps.items.models import ItemStatus

pytestmark = pytest.mark.django_db


def history_url(item) -> str:
    return reverse("audit:item-history", args=[item.public_code])


@pytest.fixture
def item_with_history(found_item, operator_user):
    record_event(
        item=found_item,
        action=AuditAction.CREATED,
        user=found_item.reported_by,
        new_status=ItemStatus.REPORTADO,
    )
    record_event(
        item=found_item,
        action=AuditAction.STATUS_CHANGED,
        user=operator_user,
        previous_status=ItemStatus.REPORTADO,
        new_status=ItemStatus.EM_CUSTODIA,
    )
    return found_item


def test_owner_sees_history_in_order(auth_client, item_with_history):
    response = auth_client.get(history_url(item_with_history))

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["action"] == AuditAction.STATUS_CHANGED
    assert data[1]["action"] == AuditAction.CREATED
    assert data[0]["item"]["public_code"] == item_with_history.public_code
    assert data[0]["responsible"]["full_name"] == "Operador de Ponto"


def test_other_user_cannot_see_history(other_client, item_with_history):
    response = other_client.get(history_url(item_with_history))
    assert response.status_code == 403


def test_operator_can_see_any_history(operator_client, item_with_history):
    response = operator_client.get(history_url(item_with_history))
    assert response.status_code == 200


def test_admin_can_see_any_history(admin_client, item_with_history):
    response = admin_client.get(history_url(item_with_history))
    assert response.status_code == 200


def test_history_requires_authentication(api_client, item_with_history):
    response = api_client.get(history_url(item_with_history))
    assert response.status_code == 401


def test_unknown_item_returns_404(auth_client):
    response = auth_client.get(reverse("audit:item-history", args=["INEXISTENTE"]))
    assert response.status_code == 404
