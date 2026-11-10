"""Testes do comando ``seed_demo``."""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone

from apps.audit.models import AuditAction, AuditEvent
from apps.items.models import FoundItem, ItemStatus, LostReport
from apps.operations.models import Claim, ClaimStatus, CollectionPoint
from apps.users.models import Role, User

pytestmark = pytest.mark.django_db

DEMO_PASSWORD = "Findly@2026!"


def _seed(**options):
    # O pytest roda com DEBUG=False; nos testes o force é o padrão.
    options.setdefault("force", True)
    return call_command("seed_demo", verbosity=0, **options)


def test_creates_the_expected_demo_dataset():
    _seed()

    assert User.objects.count() == 4
    assert CollectionPoint.objects.count() == 2
    assert FoundItem.objects.count() == 3
    assert LostReport.objects.count() == 2

    wallet = FoundItem.objects.get(public_code="DEMOACHADO")
    keys = FoundItem.objects.get(public_code="DEMOCHAVES")
    laptop = FoundItem.objects.get(public_code="DEMOCARTEI")

    assert wallet.status == ItemStatus.EM_CUSTODIA
    assert keys.status == ItemStatus.REPORTADO
    assert laptop.status == ItemStatus.AGUARDANDO_RETIRADA

    claim = Claim.objects.get(item=laptop)
    assert claim.status == ClaimStatus.APPROVED
    assert claim.withdrawal.qr_image
    assert claim.withdrawal.expires_at > timezone.now()


def test_users_receive_roles_and_password():
    _seed()

    common = User.objects.get(email="demo@findly.local")
    operator = User.objects.get(email="operador@findly.local")
    admin = User.objects.get(email="admin@findly.local")

    assert common.check_password(DEMO_PASSWORD)
    assert common.role == Role.COMMON
    assert operator.role == Role.OPERATOR
    assert operator.check_password(DEMO_PASSWORD)
    assert admin.role == Role.ADMIN
    assert admin.is_staff and admin.is_superuser


def test_audit_trail_is_recorded_for_seeded_flow():
    _seed()

    laptop = FoundItem.objects.get(public_code="DEMOCARTEI")
    actions = list(
        AuditEvent.objects.filter(item=laptop)
        .order_by("created_at", "id")
        .values_list("action", flat=True)
    )

    assert actions == [
        AuditAction.CREATED,
        AuditAction.STATUS_CHANGED,
        AuditAction.CUSTODY_TRANSFERRED,
        AuditAction.STATUS_CHANGED,
        AuditAction.CLAIM_APPROVED,
    ]


def test_is_idempotent():
    _seed()
    counts = {
        "users": User.objects.count(),
        "points": CollectionPoint.objects.count(),
        "items": FoundItem.objects.count(),
        "lost": LostReport.objects.count(),
        "claims": Claim.objects.count(),
        "events": AuditEvent.objects.count(),
    }

    _seed()

    assert {
        "users": User.objects.count(),
        "points": CollectionPoint.objects.count(),
        "items": FoundItem.objects.count(),
        "lost": LostReport.objects.count(),
        "claims": Claim.objects.count(),
        "events": AuditEvent.objects.count(),
    } == counts


def test_password_is_preserved_unless_reset_is_requested():
    _seed()
    demo = User.objects.get(email="demo@findly.local")
    demo.set_password("SenhaAlterada!2026")
    demo.save(update_fields=["password"])

    _seed()
    demo.refresh_from_db()
    assert demo.check_password("SenhaAlterada!2026")

    _seed(reset_passwords=True)
    demo.refresh_from_db()
    assert demo.check_password(DEMO_PASSWORD)


@override_settings(DEBUG=False)
def test_refuses_to_run_outside_debug_without_force():
    with pytest.raises(CommandError):
        call_command("seed_demo", verbosity=0)

    assert not User.objects.exists()


@override_settings(DEBUG=False)
def test_force_allows_running_outside_debug():
    _seed(force=True)

    assert User.objects.filter(email="demo@findly.local").exists()
