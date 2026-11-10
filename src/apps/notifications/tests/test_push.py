"""Testes do envio de Web Push e do despacho via Celery."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.test import override_settings

from apps.notifications.models import PushSubscription
from services import notification_service, push_service

pytestmark = pytest.mark.django_db

PUSH_SETTINGS = {
    "NOTIFICATIONS_PUSH_ENABLED": True,
    "VAPID_PUBLIC_KEY": "public-key",
    "VAPID_PRIVATE_KEY": "private-key",
    "VAPID_ADMIN_EMAIL": "admin@findly.local",
}


def _message(user, kind="match") -> notification_service.NotificationMessage:
    return notification_service.NotificationMessage(
        kind=kind,
        recipients=(user.email,),
        subject="Título do push",
        body="Corpo do push",
    )


def _subscription(user, **overrides) -> PushSubscription:
    data = {
        "user": user,
        "endpoint": "https://push.example.com/subscriptions/abc",
        "p256dh": "p" * 40,
        "auth": "a" * 20,
    }
    data.update(overrides)
    return PushSubscription.objects.create(**data)


@override_settings(**PUSH_SETTINGS)
def test_push_is_delivered_to_active_subscriptions(user, monkeypatch):
    subscription = _subscription(user)
    calls = []

    def fake_webpush(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(push_service, "webpush", fake_webpush)

    notification_service._deliver_push(_message(user))

    assert len(calls) == 1
    assert calls[0]["subscription_info"]["endpoint"] == subscription.endpoint
    assert calls[0]["vapid_claims"] == {"sub": "mailto:admin@findly.local"}
    subscription.refresh_from_db()
    assert subscription.last_used_at is not None


@override_settings(**PUSH_SETTINGS)
def test_expired_subscription_is_deactivated(user, monkeypatch):
    subscription = _subscription(user)

    def fake_webpush(**kwargs):
        raise push_service.WebPushException(
            "gone", response=SimpleNamespace(status_code=410)
        )

    monkeypatch.setattr(push_service, "webpush", fake_webpush)

    notification_service._deliver_push(_message(user))

    subscription.refresh_from_db()
    assert subscription.is_active is False


@override_settings(**PUSH_SETTINGS)
def test_transient_failure_keeps_subscription_active(user, monkeypatch):
    subscription = _subscription(user)

    def fake_webpush(**kwargs):
        raise push_service.WebPushException(
            "server error", response=SimpleNamespace(status_code=500)
        )

    monkeypatch.setattr(push_service, "webpush", fake_webpush)

    notification_service._deliver_push(_message(user))

    subscription.refresh_from_db()
    assert subscription.is_active is True


@override_settings(NOTIFICATIONS_PUSH_ENABLED=False)
def test_push_disabled_does_not_call_provider(user, monkeypatch):
    _subscription(user)
    called = {"value": False}

    def fake_webpush(**kwargs):
        called["value"] = True

    monkeypatch.setattr(push_service, "webpush", fake_webpush)

    notification_service._deliver_push(_message(user))

    assert called["value"] is False


@override_settings(NOTIFICATIONS_ASYNC_ENABLED=True)
def test_dispatch_enqueues_celery_task(
    user, monkeypatch, django_capture_on_commit_callbacks
):
    queued = []
    monkeypatch.setattr(
        "apps.notifications.tasks.send_notification.delay",
        lambda payload: queued.append(payload),
    )
    monkeypatch.setattr(
        notification_service,
        "deliver",
        lambda message: pytest.fail("não deveria entregar de forma síncrona"),
    )

    with django_capture_on_commit_callbacks(execute=True):
        notification_service.dispatch(_message(user))

    assert len(queued) == 1
    assert queued[0]["recipients"] == [user.email]
    assert queued[0]["subject"] == "Título do push"


@override_settings(NOTIFICATIONS_ASYNC_ENABLED=True)
def test_dispatch_falls_back_to_sync_when_broker_is_down(
    user, monkeypatch, django_capture_on_commit_callbacks
):
    def broken_delay(payload):
        raise RuntimeError("broker fora do ar")

    monkeypatch.setattr(
        "apps.notifications.tasks.send_notification.delay", broken_delay
    )
    delivered = []
    monkeypatch.setattr(notification_service, "deliver", delivered.append)

    with django_capture_on_commit_callbacks(execute=True):
        notification_service.dispatch(_message(user))

    assert len(delivered) == 1


@override_settings(NOTIFICATIONS_ASYNC_ENABLED=False)
def test_dispatch_stays_synchronous_when_async_is_disabled(
    user, monkeypatch, django_capture_on_commit_callbacks
):
    called = {"value": False}
    monkeypatch.setattr(
        "apps.notifications.tasks.send_notification.delay",
        lambda payload: called.__setitem__("value", True),
    )
    delivered = []
    monkeypatch.setattr(notification_service, "deliver", delivered.append)

    with django_capture_on_commit_callbacks(execute=True):
        notification_service.dispatch(_message(user))

    assert called["value"] is False
    assert len(delivered) == 1
