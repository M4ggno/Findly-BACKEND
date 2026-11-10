"""Testes de API dos pontos de coleta."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.operations.models import CollectionPoint

pytestmark = pytest.mark.django_db


def list_url() -> str:
    return reverse("operations:collection-point-list")


def detail_url(point: CollectionPoint) -> str:
    return reverse("operations:collection-point-detail", args=[point.pk])


def payload(**overrides):
    data = {
        "name": "Achados e Perdidos do Shopping",
        "address": "Av. Central, 500",
        "opening_hours": "Seg a Sáb, 10:00-22:00",
        "capacity": 50,
    }
    data.update(overrides)
    return data


def test_list_requires_authentication(api_client):
    assert api_client.get(list_url()).status_code == 401


def test_common_user_can_list(auth_client, point):
    response = auth_client.get(list_url())

    assert response.status_code == 200
    assert response.json()["count"] == 1
    row = response.json()["results"][0]
    assert row["name"] == point.name
    assert row["occupancy"] == 0
    assert row["has_capacity"] is True
    assert row["operators_display"][0]["id"] == point.operators.first().pk


def test_common_user_cannot_create(auth_client):
    response = auth_client.post(list_url(), payload(), format="json")
    assert response.status_code == 403


def test_operator_cannot_create(operator_client):
    response = operator_client.post(list_url(), payload(), format="json")
    assert response.status_code == 403


def test_admin_creates_point_with_operators(admin_client, operator_user):
    response = admin_client.post(
        list_url(), payload(operators=[operator_user.pk]), format="json"
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Achados e Perdidos do Shopping"
    assert data["operators"] == [operator_user.pk]
    assert data["operators_display"][0]["id"] == operator_user.pk

    point = CollectionPoint.objects.get(pk=data["id"])
    assert point.operators.filter(pk=operator_user.pk).exists()


def test_admin_cannot_assign_common_user(admin_client, common_user):
    response = admin_client.post(
        list_url(), payload(operators=[common_user.pk]), format="json"
    )

    assert response.status_code == 400
    assert "operators" in response.json()


def test_admin_updates_and_deactivates(admin_client, point):
    response = admin_client.patch(
        detail_url(point),
        {"name": "Novo nome", "is_active": False},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Novo nome"
    assert response.json()["is_active"] is False
    point.refresh_from_db()
    assert point.name == "Novo nome"
    assert point.is_active is False


def test_delete_is_not_allowed(admin_client, point):
    response = admin_client.delete(detail_url(point))
    assert response.status_code == 405
    assert CollectionPoint.objects.filter(pk=point.pk).exists()


def test_filter_by_active_and_operator(admin_client, point, other_point, operator_user):
    other_point.is_active = False
    other_point.save(update_fields=["is_active"])

    active = admin_client.get(list_url(), {"is_active": "true"})
    assert active.json()["count"] == 1
    assert active.json()["results"][0]["id"] == point.pk

    by_operator = admin_client.get(list_url(), {"operator": operator_user.pk})
    assert by_operator.json()["count"] == 2


def test_search_by_name(admin_client, point):
    found = admin_client.get(list_url(), {"search": "Recepção"})
    assert found.json()["count"] == 1

    none = admin_client.get(list_url(), {"search": "Inexistente"})
    assert none.json()["count"] == 0


def test_filter_has_capacity(auth_client, point, item_in_custody):
    point.capacity = 1
    point.save(update_fields=["capacity"])

    response = auth_client.get(list_url(), {"has_capacity": "true"})
    assert response.json()["count"] == 0
