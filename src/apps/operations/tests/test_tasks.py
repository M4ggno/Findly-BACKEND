"""Testes da limpeza agendada dos QR Codes de retirada vencidos."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from django.utils import timezone

from apps.operations.models import WithdrawalAuthority
from apps.operations.tasks import cleanup_expired_withdrawal_qrs

pytestmark = pytest.mark.django_db


def _expire(authority: WithdrawalAuthority, days_ago: int) -> Path:
    authority.expires_at = timezone.now() - timedelta(days=days_ago)
    authority.save(update_fields=["expires_at"])
    return Path(authority.qr_image.path)


def test_cleanup_removes_qr_file_after_retention(approved_claim):
    authority = WithdrawalAuthority.objects.get(claim=approved_claim)
    path = _expire(authority, days_ago=8)
    assert path.exists()

    result = cleanup_expired_withdrawal_qrs()

    assert result == {"cleaned": 1}
    assert not path.exists()
    authority.refresh_from_db()
    assert not authority.qr_image
    # O registro permanece para auditoria/histórico.
    assert WithdrawalAuthority.objects.filter(pk=authority.pk).exists()


def test_cleanup_keeps_valid_qr(approved_claim):
    authority = WithdrawalAuthority.objects.get(claim=approved_claim)
    path = Path(authority.qr_image.path)

    assert cleanup_expired_withdrawal_qrs() == {"cleaned": 0}
    assert path.exists()


def test_cleanup_keeps_recently_expired_qr(approved_claim):
    authority = WithdrawalAuthority.objects.get(claim=approved_claim)
    path = _expire(authority, days_ago=2)

    assert cleanup_expired_withdrawal_qrs() == {"cleaned": 0}
    assert path.exists()


def test_cleanup_is_idempotent(approved_claim):
    authority = WithdrawalAuthority.objects.get(claim=approved_claim)
    _expire(authority, days_ago=30)

    assert cleanup_expired_withdrawal_qrs() == {"cleaned": 1}
    assert cleanup_expired_withdrawal_qrs() == {"cleaned": 0}


def test_cleanup_accepts_custom_retention(approved_claim):
    authority = WithdrawalAuthority.objects.get(claim=approved_claim)
    path = _expire(authority, days_ago=1)

    assert cleanup_expired_withdrawal_qrs(retention_days=0) == {"cleaned": 1}
    assert not path.exists()
