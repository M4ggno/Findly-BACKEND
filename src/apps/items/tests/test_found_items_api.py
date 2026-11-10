"""Testes de API dos itens encontrados (CRUD, filtros e status)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.items.models import Category, FoundItem, ItemStatus

pytestmark = pytest.mark.django_db


def detail_url(item: FoundItem) -> str:
    return reverse("items:found-item-detail", args=[item.public_code])


def status_url(item: FoundItem) -> str:
    return reverse("items:found-item-change-status", args=[item.public_code])


def test_list_requires_authentication(api_client):
    response = api_client.get(reverse("items:found-item-list"))
    assert response.status_code == 401


def test_create_requires_authentication(api_client, found_payload):
    response = api_client.post(
        reverse("items:found-item-list"), found_payload, format="json"
    )
    assert response.status_code == 401


def test_create_sets_reporter_and_default_status(
    auth_client, common_user, found_payload
):
    response = auth_client.post(
        reverse("items:found-item-list"), found_payload, format="json"
    )

    assert response.status_code == 201
    data = response.json()
    assert data["reported_by"]["id"] == common_user.id
    assert data["reported_by"]["full_name"] == common_user.full_name
    assert "email" not in data["reported_by"]
    assert data["status"] == ItemStatus.REPORTADO
    assert len(data["public_code"]) == 10
    assert data["photos"] == []

    item = FoundItem.objects.get(public_code=data["public_code"])
    assert item.reported_by == common_user


def test_create_rejects_future_found_at(auth_client, found_payload):
    found_payload["found_at"] = (timezone.now() + timedelta(days=1)).isoformat()
    response = auth_client.post(
        reverse("items:found-item-list"), found_payload, format="json"
    )

    assert response.status_code == 400
    assert "found_at" in response.json()


def test_detail_by_public_code(auth_client, found_item):
    response = auth_client.get(detail_url(found_item))

    assert response.status_code == 200
    assert response.json()["public_code"] == found_item.public_code
    assert response.json()["title"] == found_item.title


def test_list_filters_by_status_and_category(auth_client, common_user, found_item):
    FoundItem.objects.create(
        reported_by=common_user,
        title="Celular",
        description="Tela trincada.",
        category=Category.ELETRONICOS,
        found_at=timezone.now() - timedelta(hours=1),
        found_location="Saguão",
        status=ItemStatus.EM_CUSTODIA,
    )

    by_status = auth_client.get(
        reverse("items:found-item-list"), {"status": ItemStatus.EM_CUSTODIA}
    )
    assert by_status.status_code == 200
    assert by_status.json()["count"] == 1
    assert by_status.json()["results"][0]["title"] == "Celular"

    by_category = auth_client.get(
        reverse("items:found-item-list"), {"category": Category.CARTEIRAS}
    )
    assert by_category.json()["count"] == 1
    assert by_category.json()["results"][0]["public_code"] == found_item.public_code


def test_list_search_and_mine(auth_client, common_user, other_user, found_item):
    FoundItem.objects.create(
        reported_by=other_user,
        title="Guarda-chuva",
        description="Preto, cabo de madeira.",
        category=Category.OUTROS,
        found_at=timezone.now() - timedelta(hours=3),
        found_location="Entrada principal",
    )

    search = auth_client.get(reverse("items:found-item-list"), {"search": "Carteira"})
    assert search.json()["count"] == 1

    mine = auth_client.get(reverse("items:found-item-list"), {"mine": "true"})
    assert mine.json()["count"] == 1
    assert mine.json()["results"][0]["reported_by"]["id"] == common_user.id


def test_owner_updates_while_reported(auth_client, found_item):
    response = auth_client.patch(
        detail_url(found_item), {"title": "Carteira preta (atualizada)"}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Carteira preta (atualizada)"
    found_item.refresh_from_db()
    assert found_item.title == "Carteira preta (atualizada)"


def test_owner_cannot_update_after_custody(auth_client, found_item):
    found_item.status = ItemStatus.EM_CUSTODIA
    found_item.save(update_fields=["status"])

    response = auth_client.patch(
        detail_url(found_item), {"title": "Tentativa"}, format="json"
    )

    assert response.status_code == 403


def test_other_common_user_cannot_update(other_client, found_item):
    response = other_client.patch(
        detail_url(found_item), {"title": "Tentativa"}, format="json"
    )

    assert response.status_code == 403


def test_operator_can_update_any_item(operator_client, found_item):
    response = operator_client.patch(
        detail_url(found_item), {"found_location": "Nova recepção"}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["found_location"] == "Nova recepção"


def test_common_user_cannot_change_status(auth_client, found_item):
    response = auth_client.post(
        status_url(found_item), {"status": ItemStatus.EM_CUSTODIA}, format="json"
    )

    assert response.status_code == 403


def test_operator_applies_valid_transition(operator_client, found_item):
    response = operator_client.post(
        status_url(found_item), {"status": ItemStatus.EM_CUSTODIA}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["status"] == ItemStatus.EM_CUSTODIA
    found_item.refresh_from_db()
    assert found_item.status == ItemStatus.EM_CUSTODIA


def test_operator_cannot_skip_states(operator_client, found_item):
    response = operator_client.post(
        status_url(found_item), {"status": ItemStatus.DEVOLVIDO}, format="json"
    )

    assert response.status_code == 400
    assert "status" in response.json()


def test_same_status_is_rejected(operator_client, found_item):
    response = operator_client.post(
        status_url(found_item), {"status": ItemStatus.REPORTADO}, format="json"
    )

    assert response.status_code == 400


def test_unknown_status_is_rejected(operator_client, found_item):
    response = operator_client.post(
        status_url(found_item), {"status": "ARQUIVADO"}, format="json"
    )

    assert response.status_code == 400


def test_delete_is_not_allowed(auth_client, found_item):
    response = auth_client.delete(detail_url(found_item))
    assert response.status_code == 405
    assert FoundItem.objects.filter(pk=found_item.pk).exists()
