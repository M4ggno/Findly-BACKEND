"""Testes de API e regras de negócio dos claims."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditAction, AuditEvent
from apps.items.models import ItemStatus
from apps.operations.models import Claim, ClaimStatus, WithdrawalAuthority

pytestmark = pytest.mark.django_db


def item_claims_url(item) -> str:
    return reverse("operations:item-claims", args=[item.public_code])


def list_url() -> str:
    return reverse("operations:claim-list")


def detail_url(claim: Claim) -> str:
    return reverse("operations:claim-detail", args=[claim.pk])


def action_url(claim: Claim, action: str) -> str:
    return reverse(f"operations:claim-{action}", args=[claim.pk])


def test_create_requires_authentication(api_client, item_in_custody):
    response = api_client.post(
        item_claims_url(item_in_custody), {"message": "oi"}, format="json"
    )
    assert response.status_code == 401


def test_user_opens_claim(other_client, other_user, item_in_custody):
    response = other_client.post(
        item_claims_url(item_in_custody),
        {"message": "Tenho a nota fiscal."},
        format="json",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["claimant"]["id"] == other_user.pk
    assert data["status"] == ClaimStatus.PENDING
    assert data["withdrawal"] is None

    claim = Claim.objects.get(pk=data["id"])
    assert claim.item == item_in_custody
    assert claim.message == "Tenho a nota fiscal."


def test_reporter_cannot_claim_own_found_item(
    auth_client, common_user, item_in_custody
):
    response = auth_client.post(
        item_claims_url(item_in_custody), {"message": "É meu."}, format="json"
    )

    assert response.status_code == 400


def test_terminal_item_cannot_be_claimed(other_client, item_in_custody):
    item_in_custody.status = ItemStatus.DEVOLVIDO
    item_in_custody.save(update_fields=["status"])

    response = other_client.post(
        item_claims_url(item_in_custody), {"message": "É meu."}, format="json"
    )

    assert response.status_code == 400


def test_duplicate_pending_claim_is_rejected(other_client, pending_claim):
    response = other_client.post(
        item_claims_url(pending_claim.item), {"message": "De novo."}, format="json"
    )

    assert response.status_code == 400
    assert Claim.objects.count() == 1


def test_claim_after_rejection_is_allowed(other_client, pending_claim, operator_client):
    operator_client.post(action_url(pending_claim, "reject"))

    response = other_client.post(
        item_claims_url(pending_claim.item),
        {"message": "Agora com mais provas."},
        format="json",
    )

    assert response.status_code == 201
    assert Claim.objects.filter(item=pending_claim.item).count() == 2


def test_common_user_lists_only_own_claims(other_client, common_user, item_in_custody):
    Claim.objects.create(item=item_in_custody, claimant=common_user)

    response = other_client.get(item_claims_url(item_in_custody))
    assert response.json()["count"] == 0

    own = other_client.get(item_claims_url(item_in_custody), {"mine": "true"})
    assert own.json()["count"] == 0


def test_operator_lists_all_claims(operator_client, pending_claim, common_user):
    Claim.objects.create(item=pending_claim.item, claimant=common_user)

    response = operator_client.get(item_claims_url(pending_claim.item))
    assert response.json()["count"] == 2


def test_retrieve_permissions(
    other_client, auth_client, operator_client, pending_claim
):
    assert other_client.get(detail_url(pending_claim)).status_code == 200
    assert auth_client.get(detail_url(pending_claim)).status_code == 403
    assert operator_client.get(detail_url(pending_claim)).status_code == 200


def test_global_claim_list_filters_by_status(operator_client, pending_claim):
    response = operator_client.get(list_url(), {"status": ClaimStatus.PENDING})
    assert response.json()["count"] == 1

    empty = operator_client.get(list_url(), {"status": ClaimStatus.APPROVED})
    assert empty.json()["count"] == 0


def test_approve_requires_operator_or_admin(auth_client, other_client, pending_claim):
    assert auth_client.post(action_url(pending_claim, "approve")).status_code == 403
    assert other_client.post(action_url(pending_claim, "approve")).status_code == 403


def test_operator_approves_claim(operator_client, pending_claim, operator_user, point):
    response = operator_client.post(
        action_url(pending_claim, "approve"),
        {"decision_note": "Documentação conferida."},
        format="json",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ClaimStatus.APPROVED
    assert data["reviewed_by"]["id"] == operator_user.pk
    assert data["withdrawal"]["is_valid"] is True
    assert data["withdrawal"]["qr_image"].endswith(".png")

    pending_claim.refresh_from_db()
    assert pending_claim.status == ClaimStatus.APPROVED

    item = pending_claim.item
    item.refresh_from_db()
    assert item.status == ItemStatus.AGUARDANDO_RETIRADA

    authority = WithdrawalAuthority.objects.get(claim=pending_claim)
    assert authority.expires_at > timezone.now()
    assert authority.expires_at <= timezone.now() + timedelta(hours=24, minutes=1)
    assert authority.qr_image

    actions = set(AuditEvent.objects.filter(item=item).values_list("action", flat=True))
    assert AuditAction.STATUS_CHANGED in actions
    assert AuditAction.CLAIM_APPROVED in actions

    event = AuditEvent.objects.get(action=AuditAction.CLAIM_APPROVED)
    assert event.collection_point == point
    assert event.metadata["claim"] == pending_claim.pk


def test_cannot_approve_item_not_in_custody(
    other_client, operator_client, common_user, found_item
):
    claim = Claim.objects.create(item=found_item, claimant=common_user)

    response = operator_client.post(action_url(claim, "approve"))
    assert response.status_code == 400
    claim.refresh_from_db()
    assert claim.status == ClaimStatus.PENDING


def test_approve_twice_is_rejected(operator_client, approved_claim):
    response = operator_client.post(action_url(approved_claim, "approve"))
    assert response.status_code == 400


def test_approving_rejects_other_pending_claims(
    operator_client, pending_claim, common_user
):
    other = Claim.objects.create(item=pending_claim.item, claimant=common_user)

    response = operator_client.post(action_url(pending_claim, "approve"))
    assert response.status_code == 200

    other.refresh_from_db()
    assert other.status == ClaimStatus.REJECTED
    assert "Outra reivindicação" in other.decision_note
    assert AuditEvent.objects.filter(action=AuditAction.CLAIM_REJECTED).count() == 1


def test_operator_rejects_claim(operator_client, pending_claim, operator_user):
    response = operator_client.post(
        action_url(pending_claim, "reject"),
        {"decision_note": "Documentos não conferem."},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["status"] == ClaimStatus.REJECTED

    pending_claim.refresh_from_db()
    assert pending_claim.decision_note == "Documentos não conferem."
    assert pending_claim.reviewed_by == operator_user


def test_reject_after_approval_is_rejected(operator_client, approved_claim):
    response = operator_client.post(action_url(approved_claim, "reject"))
    assert response.status_code == 400


def test_claimant_cancels_pending_claim(other_client, pending_claim):
    response = other_client.post(action_url(pending_claim, "cancel"))

    assert response.status_code == 200
    assert response.json()["status"] == ClaimStatus.CANCELLED

    event = AuditEvent.objects.get(action=AuditAction.CLAIM_CANCELLED)
    assert event.responsible == pending_claim.claimant


def test_other_user_cannot_cancel_claim(auth_client, pending_claim):
    response = auth_client.post(action_url(pending_claim, "cancel"))
    assert response.status_code == 403


def test_cancel_after_approval_is_rejected(other_client, approved_claim):
    response = other_client.post(action_url(approved_claim, "cancel"))
    assert response.status_code == 400


def test_claim_on_item_without_custody_can_be_opened(other_client, found_item):
    response = other_client.post(
        item_claims_url(found_item), {"message": "É meu."}, format="json"
    )

    assert response.status_code == 201
    assert Claim.objects.filter(item=found_item).count() == 1
