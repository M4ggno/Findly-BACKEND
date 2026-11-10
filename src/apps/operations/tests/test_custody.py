"""Testes de custódia: histórico, transferências e auditoria."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditAction, AuditEvent
from apps.items.models import Category, FoundItem, ItemStatus
from apps.operations.models import CustodyRecord

pytestmark = pytest.mark.django_db


def custody_url(item: FoundItem) -> str:
    return reverse("operations:item-custody", args=[item.public_code])


def transfer_url(item: FoundItem) -> str:
    return reverse("operations:custody-transfer", args=[item.public_code])


def test_history_requires_authentication(api_client, item_in_custody):
    assert api_client.get(custody_url(item_in_custody)).status_code == 401


def test_owner_sees_history(auth_client, item_in_custody):
    response = auth_client.get(custody_url(item_in_custody))

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_history_serializes_holder(auth_client, item_in_custody, point):
    response = auth_client.get(custody_url(item_in_custody))

    row = response.json()[0]
    assert row["collection_point"]["id"] == point.pk
    assert row["collection_point"]["name"] == point.name
    assert row["held_by_user"] is None
    assert row["is_active"] is True
    assert row["ended_at"] is None


def test_other_common_user_cannot_see_history(other_client, item_in_custody):
    assert other_client.get(custody_url(item_in_custody)).status_code == 403


def test_operator_and_admin_see_history(operator_client, admin_client, item_in_custody):
    assert operator_client.get(custody_url(item_in_custody)).status_code == 200
    assert admin_client.get(custody_url(item_in_custody)).status_code == 200


def test_unknown_item_returns_404(auth_client):
    response = auth_client.get(reverse("operations:item-custody", args=["NAOEXISTE"]))
    assert response.status_code == 404


def test_creation_opens_initial_custody(auth_client, common_user, found_payload):
    response = auth_client.post(
        reverse("items:found-item-list"), found_payload, format="json"
    )

    assert response.status_code == 201
    item = FoundItem.objects.get(public_code=response.json()["public_code"])
    record = CustodyRecord.objects.get(item=item, ended_at__isnull=True)
    assert record.held_by_user == common_user
    assert record.collection_point is None
    # A criação registra só o evento CREATED (sem duplicar custódia).
    assert AuditEvent.objects.filter(item=item).count() == 1


def test_transfer_requires_authentication(api_client, found_item, point):
    response = api_client.post(
        transfer_url(found_item), {"collection_point": point.pk}, format="json"
    )
    assert response.status_code == 401


def test_common_user_cannot_transfer(auth_client, found_item, point):
    response = auth_client.post(
        transfer_url(found_item), {"collection_point": point.pk}, format="json"
    )
    assert response.status_code == 403


def test_operator_transfers_reported_item_to_point(
    operator_client, found_item, point, operator_user
):
    response = operator_client.post(
        transfer_url(found_item),
        {"collection_point": point.pk, "note": "Recebido na portaria"},
        format="json",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["collection_point"]["id"] == point.pk
    assert data["is_active"] is True

    found_item.refresh_from_db()
    assert found_item.status == ItemStatus.EM_CUSTODIA

    records = CustodyRecord.objects.filter(item=found_item)
    assert records.count() == 1

    actions = list(
        AuditEvent.objects.filter(item=found_item)
        .order_by("created_at")
        .values_list("action", flat=True)
    )
    assert actions == [AuditAction.STATUS_CHANGED, AuditAction.CUSTODY_TRANSFERRED]
    event = AuditEvent.objects.get(action=AuditAction.CUSTODY_TRANSFERRED)
    assert event.collection_point == point
    assert event.responsible == operator_user
    assert event.previous_status == ItemStatus.REPORTADO
    assert event.new_status == ItemStatus.EM_CUSTODIA
    assert event.metadata["to"]["collection_point"] == point.pk


def test_transfer_closes_previous_record(item_in_custody, operator_client, other_point):
    response = operator_client.post(
        transfer_url(item_in_custody),
        {"collection_point": other_point.pk},
        format="json",
    )

    assert response.status_code == 201
    item_in_custody.refresh_from_db()
    assert item_in_custody.status == ItemStatus.EM_CUSTODIA

    records = CustodyRecord.objects.filter(item=item_in_custody).order_by("started_at")
    assert records.count() == 2
    assert records[0].ended_at is not None
    assert records[1].ended_at is None
    assert records[1].collection_point == other_point

    event = AuditEvent.objects.get(action=AuditAction.CUSTODY_TRANSFERRED)
    assert event.collection_point == other_point


def test_operator_must_be_assigned_to_point(operator_client, found_item, operator_user):
    from apps.operations.models import CollectionPoint
    from apps.users.models import User

    unassigned = CollectionPoint.objects.create(
        name="Ponto sem operador", address="Rua X, 1"
    )
    other_operator = User.objects.create_user(
        email="segundo@findly.local",
        password="S3nh@Forte!2026",
        full_name="Segundo Operador",
        role="operator",
    )
    unassigned.operators.add(other_operator)

    response = operator_client.post(
        transfer_url(found_item), {"collection_point": unassigned.pk}, format="json"
    )

    assert response.status_code == 400
    assert "responsável" in response.json()["detail"].lower()
    found_item.refresh_from_db()
    assert found_item.status == ItemStatus.REPORTADO


def test_inactive_point_is_rejected(operator_client, found_item, point):
    from apps.operations.models import CollectionPoint

    point.is_active = False
    point.save(update_fields=["is_active"])

    response = operator_client.post(
        transfer_url(found_item), {"collection_point": point.pk}, format="json"
    )

    assert response.status_code == 400
    assert CollectionPoint.objects.filter(pk=point.pk).exists()


def test_capacity_is_enforced(operator_client, found_item, point, common_user):
    # O ponto já tem um item ativo (item_in_custody via fixture manual).
    point.capacity = 1
    point.save(update_fields=["capacity"])
    CustodyRecord.objects.create(item=found_item, collection_point=point)

    second = FoundItem.objects.create(
        reported_by=common_user,
        title="Celular",
        description="Tela trincada.",
        category=Category.ELETRONICOS,
        found_at=timezone.now() - timedelta(hours=1),
        found_location="Saguão",
    )

    response = operator_client.post(
        transfer_url(second), {"collection_point": point.pk}, format="json"
    )

    assert response.status_code == 400
    assert "capacidade" in response.json()["detail"].lower()


def test_transfer_to_same_point_is_rejected(operator_client, item_in_custody, point):
    response = operator_client.post(
        transfer_url(item_in_custody), {"collection_point": point.pk}, format="json"
    )

    assert response.status_code == 400
    assert "já está" in response.json()["detail"].lower()


def test_terminal_item_cannot_be_transferred(operator_client, found_item, point):
    found_item.status = ItemStatus.DEVOLVIDO
    found_item.save(update_fields=["status"])

    response = operator_client.post(
        transfer_url(found_item), {"collection_point": point.pk}, format="json"
    )

    assert response.status_code == 400


def test_awaiting_pickup_cannot_be_transferred(
    operator_client, item_in_custody, other_point
):
    item_in_custody.status = ItemStatus.AGUARDANDO_RETIRADA
    item_in_custody.save(update_fields=["status"])

    response = operator_client.post(
        transfer_url(item_in_custody),
        {"collection_point": other_point.pk},
        format="json",
    )

    assert response.status_code == 400


def test_invalid_point_id_is_rejected(operator_client, found_item):
    response = operator_client.post(
        transfer_url(found_item), {"collection_point": 999999}, format="json"
    )
    assert response.status_code == 400
    assert "collection_point" in response.json()
