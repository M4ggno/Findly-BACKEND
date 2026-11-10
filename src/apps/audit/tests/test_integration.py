"""Integração: toda criação/transição de item gera auditoria atomicamente."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.audit.models import AuditAction, AuditEvent
from apps.items.models import FoundItem, ItemStatus
from apps.items.services import InvalidStatusTransition, transition_found_item

pytestmark = pytest.mark.django_db


def test_transition_creates_audit_event(found_item, operator_user):
    transition_found_item(found_item, ItemStatus.EM_CUSTODIA, user=operator_user)

    event = AuditEvent.objects.get()
    assert event.item == found_item
    assert event.action == AuditAction.STATUS_CHANGED
    assert event.previous_status == ItemStatus.REPORTADO
    assert event.new_status == ItemStatus.EM_CUSTODIA
    assert event.responsible == operator_user


def test_invalid_transition_creates_no_event(found_item, operator_user):
    with pytest.raises(InvalidStatusTransition):
        transition_found_item(found_item, ItemStatus.DEVOLVIDO, user=operator_user)

    assert AuditEvent.objects.count() == 0


def test_audit_failure_rolls_back_transition(found_item, operator_user, monkeypatch):
    def _fail(**kwargs):
        raise RuntimeError("falha simulada na auditoria")

    monkeypatch.setattr("apps.audit.services.record_event", _fail)

    with pytest.raises(RuntimeError):
        transition_found_item(found_item, ItemStatus.EM_CUSTODIA, user=operator_user)

    found_item.refresh_from_db()
    assert found_item.status == ItemStatus.REPORTADO
    assert AuditEvent.objects.count() == 0


def test_api_create_records_created_event(auth_client, common_user, found_payload):
    response = auth_client.post(
        reverse("items:found-item-list"), found_payload, format="json"
    )

    assert response.status_code == 201
    item = FoundItem.objects.get(public_code=response.json()["public_code"])

    event = AuditEvent.objects.get()
    assert event.item == item
    assert event.action == AuditAction.CREATED
    assert event.previous_status == ""
    assert event.new_status == ItemStatus.REPORTADO
    assert event.responsible == common_user


def test_api_create_rolls_back_when_audit_fails(
    auth_client, found_payload, monkeypatch
):
    def _fail(**kwargs):
        raise RuntimeError("falha simulada na auditoria")

    monkeypatch.setattr("apps.audit.services.record_event", _fail)

    with pytest.raises(RuntimeError):
        auth_client.post(reverse("items:found-item-list"), found_payload, format="json")

    assert FoundItem.objects.count() == 0
    assert AuditEvent.objects.count() == 0
