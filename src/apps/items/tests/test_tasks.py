"""Testes das tarefas agendadas do app de itens e do comando de agendamento."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone
from django_celery_beat.models import PeriodicTask

from apps.audit.models import AuditAction, AuditEvent
from apps.items.models import ItemStatus, LostReportStatus
from apps.items.tasks import expire_found_items, expire_lost_reports
from apps.operations.models import Claim, ClaimStatus

pytestmark = pytest.mark.django_db


def _age_item(item, days: int) -> None:
    type(item).objects.filter(pk=item.pk).update(
        updated_at=timezone.now() - timedelta(days=days)
    )


def _age_lost_report(report, days: int) -> None:
    type(report).objects.filter(pk=report.pk).update(
        lost_at=timezone.now() - timedelta(days=days)
    )


def test_expire_found_items_moves_inactive_item_to_expired(found_item):
    _age_item(found_item, days=91)

    result = expire_found_items()

    assert result == {"expired": 1, "rejected_claims": 0}
    found_item.refresh_from_db()
    assert found_item.status == ItemStatus.EXPIRADO

    event = AuditEvent.objects.get(item=found_item, action=AuditAction.STATUS_CHANGED)
    assert event.responsible is None
    assert event.previous_status == ItemStatus.REPORTADO
    assert event.new_status == ItemStatus.EXPIRADO


def test_expire_found_items_keeps_recent_items(found_item):
    _age_item(found_item, days=10)

    assert expire_found_items() == {"expired": 0, "rejected_claims": 0}
    found_item.refresh_from_db()
    assert found_item.status == ItemStatus.REPORTADO


def test_expire_found_items_ignores_terminal_items(found_item):
    found_item.status = ItemStatus.DEVOLVIDO
    found_item.save(update_fields=["status"])
    _age_item(found_item, days=200)

    assert expire_found_items() == {"expired": 0, "rejected_claims": 0}
    found_item.refresh_from_db()
    assert found_item.status == ItemStatus.DEVOLVIDO


def test_expire_found_items_rejects_pending_claims(found_item, other_user):
    claim = Claim.objects.create(item=found_item, claimant=other_user)
    _age_item(found_item, days=91)

    result = expire_found_items()

    assert result == {"expired": 1, "rejected_claims": 1}
    claim.refresh_from_db()
    assert claim.status == ClaimStatus.REJECTED
    assert "expirado" in claim.decision_note.lower()
    assert claim.reviewed_by is None

    event = AuditEvent.objects.get(item=found_item, action=AuditAction.CLAIM_REJECTED)
    assert event.responsible is None


def test_expire_found_items_accepts_custom_window(found_item):
    _age_item(found_item, days=5)

    assert expire_found_items(days=3)["expired"] == 1


def test_expire_lost_reports_closes_old_open_reports(lost_report):
    _age_lost_report(lost_report, days=91)

    result = expire_lost_reports()

    assert result == {"expired": 1}
    lost_report.refresh_from_db()
    assert lost_report.status == LostReportStatus.EXPIRADO


def test_expire_lost_reports_keeps_recent_and_closed(lost_report, other_user):
    from apps.items.models import Category, LostReport

    recent = LostReport.objects.create(
        owner=other_user,
        title="Guarda-chuva",
        description="Guarda-chuva azul.",
        category=Category.OUTROS,
        lost_at=timezone.now() - timedelta(days=3),
        lost_location="Saguão",
    )
    cancelled = LostReport.objects.create(
        owner=other_user,
        title="Mochila",
        description="Mochila cinza.",
        category=Category.OUTROS,
        lost_at=timezone.now() - timedelta(days=200),
        lost_location="Saguão",
        status=LostReportStatus.CANCELADO,
    )

    assert expire_lost_reports() == {"expired": 0}
    recent.refresh_from_db()
    cancelled.refresh_from_db()
    assert recent.status == LostReportStatus.ABERTO
    assert cancelled.status == LostReportStatus.CANCELADO


def test_setup_periodic_tasks_is_idempotent():
    call_command("setup_periodic_tasks")

    names = set(PeriodicTask.objects.values_list("name", flat=True))
    assert names == {
        "Findly — expirar itens achados",
        "Findly — expirar alertas de perda",
        "Findly — limpar QR de retirada vencidos",
    }
    assert PeriodicTask.objects.filter(enabled=True).count() == 3

    call_command("setup_periodic_tasks")
    assert PeriodicTask.objects.count() == 3

    task = PeriodicTask.objects.get(name="Findly — expirar itens achados")
    assert task.task == "apps.items.tasks.expire_found_items"
    assert task.crontab.hour == "3"
    assert task.crontab.minute == "0"
