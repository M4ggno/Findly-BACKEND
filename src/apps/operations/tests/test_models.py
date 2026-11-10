"""Testes dos modelos de operações e do serviço de QR Code."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.operations.models import (
    Claim,
    ClaimStatus,
    CustodyRecord,
    WithdrawalAuthority,
)
from services.qrcode_service import (
    build_qr_png,
    extract_withdrawal_token,
    item_label_payload,
    withdrawal_payload,
)

pytestmark = pytest.mark.django_db


def test_collection_point_occupancy_and_capacity(point, item_in_custody):
    point.refresh_from_db()
    assert point.current_occupancy == 1
    assert point.has_capacity is True

    point.capacity = 1
    point.save(update_fields=["capacity"])
    point.refresh_from_db()
    assert point.has_capacity is False


def test_collection_point_without_capacity_is_unlimited(point, item_in_custody):
    point.capacity = None
    point.save(update_fields=["capacity"])
    point.refresh_from_db()
    assert point.has_capacity is True


def test_custody_requires_a_holder(found_item):
    with pytest.raises(IntegrityError):
        CustodyRecord.objects.create(item=found_item)


def test_custody_has_only_one_active_record(item_in_custody, other_point):
    with pytest.raises(IntegrityError):
        CustodyRecord.objects.create(item=item_in_custody, collection_point=other_point)


def test_custody_str_uses_point(item_in_custody, point):
    record = CustodyRecord.objects.get(item=item_in_custody, ended_at__isnull=True)
    assert point.name in str(record)
    assert item_in_custody.public_code in str(record)


def test_claim_only_one_pending_per_user_and_item(item_in_custody, other_user):
    data = {
        "item": item_in_custody,
        "claimant": other_user,
        "message": "Primeira",
    }
    Claim.objects.create(**data)

    with pytest.raises(IntegrityError):
        Claim.objects.create(**{**data, "message": "Segunda"})


def test_claim_only_one_approved_per_item(item_in_custody, other_user, common_user):
    Claim.objects.create(
        item=item_in_custody,
        claimant=other_user,
        status=ClaimStatus.APPROVED,
    )
    with pytest.raises(IntegrityError):
        Claim.objects.create(
            item=item_in_custody,
            claimant=common_user,
            status=ClaimStatus.APPROVED,
        )


def test_withdrawal_authority_validity(pending_claim, operator_user):
    now = timezone.now()
    authority = WithdrawalAuthority.objects.create(
        claim=pending_claim,
        expires_at=now + timedelta(hours=24),
        created_by=operator_user,
    )
    assert authority.is_valid is True
    assert authority.is_expired is False

    authority.used_at = now
    assert authority.is_valid is False

    authority.used_at = None
    authority.expires_at = now - timedelta(seconds=1)
    assert authority.is_expired is True
    assert authority.is_valid is False


def test_withdrawal_authority_str(pending_claim, operator_user):
    authority = WithdrawalAuthority.objects.create(
        claim=pending_claim,
        expires_at=timezone.now() + timedelta(hours=1),
        created_by=operator_user,
    )
    assert pending_claim.item.public_code in str(authority)


def test_qrcode_service_generates_png():
    content = build_qr_png("FINDLY:TESTE")
    assert content.name == "qrcode.png"
    assert content.read(8) == b"\x89PNG\r\n\x1a\n"


def test_qrcode_payload_helpers(item_in_custody):
    assert item_label_payload(item_in_custody) == (
        f"FINDLY:{item_in_custody.public_code}"
    )
    payload = withdrawal_payload("abc123")
    assert payload == "FINDLY:WITHDRAWAL:abc123"
    assert extract_withdrawal_token(payload) == "abc123"
    assert extract_withdrawal_token("abc123") == "abc123"
    assert extract_withdrawal_token("  ") == ""


def test_audit_action_catalogue():
    assert AuditAction.CLAIM_CANCELLED in AuditAction.values
    assert AuditAction.WITHDRAWAL_CONFIRMED in AuditAction.values
