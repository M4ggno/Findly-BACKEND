"""Testes da API de inscrições de push."""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.notifications.models import PushSubscription

pytestmark = pytest.mark.django_db

ENDPOINT = "https://push.example.com/subscriptions/abc123"


def _payload(**overrides) -> dict:
    data = {
        "endpoint": ENDPOINT,
        "keys": {"p256dh": "p" * 40, "auth": "a" * 20},
        "user_agent": "pytest/1.0",
    }
    data.update(overrides)
    return data


def test_requires_authentication():
    response = APIClient().get(reverse("notifications:subscription-list"))

    assert response.status_code == 401


def test_create_and_list_subscription(auth_client, user):
    response = auth_client.post(
        reverse("notifications:subscription-list"), _payload(), format="json"
    )

    assert response.status_code == 201
    body = response.json()
    assert body["endpoint"] == ENDPOINT
    assert body["keys"] == {"p256dh": "p" * 40, "auth": "a" * 20}

    subscription = PushSubscription.objects.get()
    assert subscription.user == user
    assert subscription.is_active is True

    listing = auth_client.get(reverse("notifications:subscription-list"))
    assert listing.status_code == 200
    assert [item["endpoint"] for item in listing.json()] == [ENDPOINT]


def test_resubmitting_same_endpoint_updates_instead_of_duplicating(auth_client, user):
    auth_client.post(
        reverse("notifications:subscription-list"), _payload(), format="json"
    )

    response = auth_client.post(
        reverse("notifications:subscription-list"),
        _payload(
            keys={"p256dh": "q" * 40, "auth": "b" * 20},
            user_agent="pytest/2.0",
        ),
        format="json",
    )

    assert response.status_code == 201
    assert PushSubscription.objects.count() == 1
    subscription = PushSubscription.objects.get()
    assert subscription.user == user
    assert subscription.p256dh == "q" * 40
    assert subscription.user_agent == "pytest/2.0"


def test_same_endpoint_rebinds_to_the_user_that_logged_in(
    auth_client, other_client, user, other_user
):
    auth_client.post(
        reverse("notifications:subscription-list"), _payload(), format="json"
    )

    response = other_client.post(
        reverse("notifications:subscription-list"), _payload(), format="json"
    )

    assert response.status_code == 201
    assert PushSubscription.objects.count() == 1
    assert PushSubscription.objects.get().user == other_user


def test_missing_keys_is_rejected(auth_client):
    response = auth_client.post(
        reverse("notifications:subscription-list"),
        {"endpoint": ENDPOINT},
        format="json",
    )

    assert response.status_code == 400
    assert "keys" in response.json()
    assert PushSubscription.objects.count() == 0


def test_list_only_returns_own_subscriptions(auth_client, user, other_user):
    PushSubscription.objects.create(
        user=user, endpoint=ENDPOINT, p256dh="p" * 40, auth="a" * 20
    )
    PushSubscription.objects.create(
        user=other_user,
        endpoint="https://push.example.com/subscriptions/other",
        p256dh="p" * 40,
        auth="a" * 20,
    )

    response = auth_client.get(reverse("notifications:subscription-list"))

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["endpoint"] == ENDPOINT


def test_delete_own_subscription(auth_client, user):
    subscription = PushSubscription.objects.create(
        user=user, endpoint=ENDPOINT, p256dh="p" * 40, auth="a" * 20
    )

    response = auth_client.delete(
        reverse("notifications:subscription-detail", args=[subscription.pk])
    )

    assert response.status_code == 204
    assert PushSubscription.objects.count() == 0


def test_cannot_delete_someone_elses_subscription(auth_client, other_user):
    subscription = PushSubscription.objects.create(
        user=other_user, endpoint=ENDPOINT, p256dh="p" * 40, auth="a" * 20
    )

    response = auth_client.delete(
        reverse("notifications:subscription-detail", args=[subscription.pk])
    )

    assert response.status_code == 404
    assert PushSubscription.objects.count() == 1
