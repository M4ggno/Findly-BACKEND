"""Testes da consulta administrativa de auditoria."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_event
from apps.items.models import ItemStatus

pytestmark = pytest.mark.django_db


def list_url() -> str:
    return reverse("audit:audit-event-list")


def detail_url(event) -> str:
    return reverse("audit:audit-event-detail", args=[event.pk])


@pytest.fixture
def event(found_item, operator_user):
    return record_event(
        item=found_item,
        action=AuditAction.STATUS_CHANGED,
        user=operator_user,
        previous_status=ItemStatus.REPORTADO,
        new_status=ItemStatus.EM_CUSTODIA,
    )


def test_list_requires_authentication(api_client):
    response = api_client.get(list_url())
    assert response.status_code == 401


@pytest.mark.parametrize("client_fixture", ["auth_client", "operator_client"])
def test_list_is_admin_only(client_fixture, request, event):
    client = request.getfixturevalue(client_fixture)
    response = client.get(list_url())
    assert response.status_code == 403


def test_admin_lists_events(admin_client, event):
    response = admin_client.get(list_url())

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["results"][0]["action"] == AuditAction.STATUS_CHANGED
    assert data["results"][0]["item"]["public_code"] == event.item.public_code


def test_admin_retrieves_event(admin_client, event):
    response = admin_client.get(detail_url(event))

    assert response.status_code == 200
    assert response.json()["id"] == event.pk
    assert response.json()["metadata"] == {}


def test_filter_by_item_and_action(admin_client, event, common_user, found_item):
    from apps.items.models import FoundItem

    other_item = FoundItem.objects.create(
        reported_by=common_user,
        title="Celular",
        description="Tela trincada.",
        found_at=timezone.now() - timedelta(hours=1),
        found_location="Saguão",
    )
    record_event(
        item=other_item,
        action=AuditAction.CREATED,
        user=common_user,
        new_status=ItemStatus.REPORTADO,
    )

    by_item = admin_client.get(list_url(), {"item": found_item.public_code})
    assert by_item.json()["count"] == 1

    by_action = admin_client.get(list_url(), {"action": AuditAction.CREATED})
    assert by_action.json()["count"] == 1
    assert (
        by_action.json()["results"][0]["item"]["public_code"] == other_item.public_code
    )


def test_filter_by_date_range(admin_client, event):
    now = timezone.now()
    inside = admin_client.get(
        list_url(),
        {
            "date_from": (now - timedelta(hours=1)).isoformat(),
            "date_to": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert inside.json()["count"] == 1

    past = admin_client.get(
        list_url(),
        {
            "date_from": (now - timedelta(days=2)).isoformat(),
            "date_to": (now - timedelta(days=1)).isoformat(),
        },
    )
    assert past.json()["count"] == 0


def test_search_by_item_title(admin_client, event):
    response = admin_client.get(list_url(), {"search": "Carteira"})
    assert response.json()["count"] == 1

    none = admin_client.get(list_url(), {"search": "Bicicleta"})
    assert none.json()["count"] == 0


def test_ordering_ascending(admin_client, event, common_user, found_item):
    second = record_event(
        item=found_item,
        action=AuditAction.CREATED,
        user=common_user,
        new_status=ItemStatus.REPORTADO,
    )

    response = admin_client.get(list_url(), {"ordering": "created_at"})
    ids = [row["id"] for row in response.json()["results"]]
    assert ids == [event.pk, second.pk]


def test_write_methods_are_not_allowed(admin_client, event):
    assert admin_client.post(list_url(), {}, format="json").status_code == 405
    assert admin_client.patch(detail_url(event), {}, format="json").status_code == 405
    assert admin_client.delete(detail_url(event)).status_code == 405
