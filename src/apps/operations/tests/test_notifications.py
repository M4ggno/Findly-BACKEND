"""Testes das notificações disparadas pelo app de operações."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.operations.models import WithdrawalAuthority
from services import notification_service

pytestmark = pytest.mark.django_db


def transfer_url(item) -> str:
    return reverse("operations:custody-transfer", args=[item.public_code])


def confirm_url() -> str:
    return reverse("operations:withdrawal-confirm")


def action_url(claim, action: str) -> str:
    return reverse(f"operations:claim-{action}", args=[claim.pk])


def test_transfer_notifies_item_reporter(
    operator_client,
    found_item,
    point,
    common_user,
    mailoutbox,
    django_capture_on_commit_callbacks,
):
    with django_capture_on_commit_callbacks(execute=True):
        response = operator_client.post(
            transfer_url(found_item), {"collection_point": point.pk}, format="json"
        )

    assert response.status_code == 201
    assert len(mailoutbox) == 1
    message = mailoutbox[0]
    assert message.to == [common_user.email]
    assert point.name in message.body
    assert found_item.public_code in message.body


def test_approval_notifies_claimant(
    operator_client,
    pending_claim,
    other_user,
    point,
    mailoutbox,
    django_capture_on_commit_callbacks,
):
    with django_capture_on_commit_callbacks(execute=True):
        response = operator_client.post(action_url(pending_claim, "approve"))

    assert response.status_code == 200
    assert len(mailoutbox) == 1
    message = mailoutbox[0]
    assert message.to == [other_user.email]
    assert "Retirada liberada" in message.subject
    assert point.name in message.body
    assert pending_claim.item.public_code in message.body


def test_withdrawal_notifies_claimant_and_reporter(
    operator_client,
    approved_claim,
    other_user,
    common_user,
    point,
    mailoutbox,
    django_capture_on_commit_callbacks,
):
    authority = WithdrawalAuthority.objects.get(claim=approved_claim)

    with django_capture_on_commit_callbacks(execute=True):
        response = operator_client.post(
            confirm_url(), {"token": authority.token}, format="json"
        )

    assert response.status_code == 200
    assert len(mailoutbox) == 1
    message = mailoutbox[0]
    assert message.to == [other_user.email, common_user.email]
    assert "Entrega concluída" in message.subject
    assert point.name in message.body
    assert approved_claim.item.public_code in message.body


def test_notification_failure_does_not_break_transfer(
    operator_client,
    found_item,
    point,
    monkeypatch,
    django_capture_on_commit_callbacks,
):
    def boom(*args, **kwargs):
        raise RuntimeError("SMTP fora do ar")

    monkeypatch.setattr(notification_service, "send_mail", boom)

    with django_capture_on_commit_callbacks(execute=True):
        response = operator_client.post(
            transfer_url(found_item), {"collection_point": point.pk}, format="json"
        )

    assert response.status_code == 201
    found_item.refresh_from_db()
    assert found_item.status == "EM_CUSTODIA"
