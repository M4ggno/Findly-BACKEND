"""Testes da retirada via QR Code."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditAction, AuditEvent
from apps.items.models import ItemStatus
from apps.operations.models import CustodyRecord, WithdrawalAuthority
from apps.operations.services import approve_claim

pytestmark = pytest.mark.django_db


def confirm_url() -> str:
    return reverse("operations:withdrawal-confirm")


def label_url(item) -> str:
    return reverse("operations:item-label", args=[item.public_code])


def test_confirm_requires_operator(api_client, auth_client):
    assert api_client.post(confirm_url(), {"token": "x"}).status_code == 401
    assert auth_client.post(confirm_url(), {"token": "x"}).status_code == 403


def test_confirm_requires_token(operator_client):
    response = operator_client.post(confirm_url(), {}, format="json")
    assert response.status_code == 400
    assert "token" in response.json()


def test_confirm_invalid_token(operator_client):
    response = operator_client.post(
        confirm_url(), {"token": "token-invalido"}, format="json"
    )
    assert response.status_code == 400
    assert "inválido" in response.json()["detail"].lower()


def test_confirm_valid_token_completes_withdrawal(
    operator_client, approved_claim, operator_user, point
):
    authority = WithdrawalAuthority.objects.get(claim=approved_claim)
    item = approved_claim.item

    response = operator_client.post(
        confirm_url(), {"token": authority.token}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["detail"] == "Retirada confirmada."
    assert response.json()["item"]["status"] == ItemStatus.DEVOLVIDO

    item.refresh_from_db()
    assert item.status == ItemStatus.DEVOLVIDO

    authority.refresh_from_db()
    assert authority.used_at is not None

    active = CustodyRecord.objects.filter(item=item, ended_at__isnull=True)
    assert not active.exists()

    event = AuditEvent.objects.get(action=AuditAction.WITHDRAWAL_CONFIRMED)
    assert event.responsible == operator_user
    assert event.collection_point == point
    assert event.previous_status == ItemStatus.AGUARDANDO_RETIRADA
    assert event.new_status == ItemStatus.DEVOLVIDO
    assert event.metadata["claim"] == approved_claim.pk


def test_confirm_accepts_qr_payload(operator_client, approved_claim):
    authority = WithdrawalAuthority.objects.get(claim=approved_claim)
    payload = f"FINDLY:WITHDRAWAL:{authority.token}"

    response = operator_client.post(confirm_url(), {"token": payload}, format="json")

    assert response.status_code == 200
    approved_claim.item.refresh_from_db()
    assert approved_claim.item.status == ItemStatus.DEVOLVIDO


def test_confirm_twice_is_rejected(operator_client, approved_claim):
    authority = WithdrawalAuthority.objects.get(claim=approved_claim)
    first = operator_client.post(
        confirm_url(), {"token": authority.token}, format="json"
    )
    assert first.status_code == 200

    second = operator_client.post(
        confirm_url(), {"token": authority.token}, format="json"
    )
    assert second.status_code == 400
    assert "já foi utilizado" in second.json()["detail"].lower()


def test_expired_token_is_rejected(operator_client, approved_claim):
    authority = WithdrawalAuthority.objects.get(claim=approved_claim)
    authority.expires_at = timezone.now() - timedelta(minutes=1)
    authority.save(update_fields=["expires_at"])

    response = operator_client.post(
        confirm_url(), {"token": authority.token}, format="json"
    )

    assert response.status_code == 400
    assert "expirou" in response.json()["detail"].lower()
    approved_claim.item.refresh_from_db()
    assert approved_claim.item.status == ItemStatus.AGUARDANDO_RETIRADA


def test_claim_must_be_approved(operator_client, pending_claim, operator_user):
    authority = WithdrawalAuthority.objects.create(
        claim=pending_claim,
        expires_at=timezone.now() + timedelta(hours=1),
        created_by=operator_user,
    )

    response = operator_client.post(
        confirm_url(), {"token": authority.token}, format="json"
    )

    assert response.status_code == 400
    assert "não está aprovada" in response.json()["detail"].lower()


def test_item_must_be_awaiting_pickup(operator_client, approved_claim, operator_user):
    authority = WithdrawalAuthority.objects.get(claim=approved_claim)
    item = approved_claim.item
    item.status = ItemStatus.EM_CUSTODIA
    item.save(update_fields=["status"])

    response = operator_client.post(
        confirm_url(), {"token": authority.token}, format="json"
    )

    assert response.status_code == 400
    assert "não está aguardando" in response.json()["detail"].lower()


def test_approve_claim_creates_qr_file(approved_claim):
    authority = WithdrawalAuthority.objects.get(claim=approved_claim)
    assert authority.qr_image.name.endswith(".png")

    from pathlib import Path

    assert Path(authority.qr_image.path).exists()
    assert Path(authority.qr_image.path).stat().st_size > 0


def test_item_label_returns_png(auth_client, found_item):
    response = auth_client.get(label_url(found_item))

    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_item_label_permissions(other_client, operator_client, found_item):
    assert other_client.get(label_url(found_item)).status_code == 403
    assert operator_client.get(label_url(found_item)).status_code == 200


def test_item_label_requires_authentication(api_client, found_item):
    assert api_client.get(label_url(found_item)).status_code == 401


def test_approved_claim_in_claim_detail_exposes_qr(operator_client, approved_claim):
    url = reverse("operations:claim-detail", args=[approved_claim.pk])
    response = operator_client.get(url)

    assert response.status_code == 200
    withdrawal = response.json()["withdrawal"]
    assert withdrawal["is_valid"] is True
    assert withdrawal["qr_image"].startswith("http")


def test_terminal_item_cannot_be_claimed_after_withdrawal(
    operator_client, approved_claim, other_client
):
    authority = WithdrawalAuthority.objects.get(claim=approved_claim)
    operator_client.post(confirm_url(), {"token": authority.token}, format="json")

    response = other_client.post(
        reverse("operations:item-claims", args=[approved_claim.item.public_code]),
        {"message": "Quero reivindicar."},
        format="json",
    )
    assert response.status_code == 400


def test_direct_service_approval_requires_custody(
    found_item, operator_user, common_user
):
    from apps.operations.models import Claim
    from apps.operations.services import InvalidClaim

    claim = Claim.objects.create(item=found_item, claimant=common_user)
    with pytest.raises(InvalidClaim):
        approve_claim(claim, user=operator_user)
