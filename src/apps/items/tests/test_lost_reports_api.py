"""Testes de API dos alertas de item perdido."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.items.models import Category, LostReport, LostReportStatus

pytestmark = pytest.mark.django_db


def detail_url(report: LostReport) -> str:
    return reverse("items:lost-report-detail", args=[report.public_code])


def cancel_url(report: LostReport) -> str:
    return reverse("items:lost-report-cancel", args=[report.public_code])


def test_create_sets_owner_and_open_status(auth_client, common_user, lost_payload):
    response = auth_client.post(
        reverse("items:lost-report-list"), lost_payload, format="json"
    )

    assert response.status_code == 201
    data = response.json()
    assert data["owner"]["id"] == common_user.id
    assert "email" not in data["owner"]
    assert data["status"] == LostReportStatus.ABERTO
    assert len(data["public_code"]) == 10

    report = LostReport.objects.get(public_code=data["public_code"])
    assert report.owner == common_user


def test_create_rejects_future_lost_at(auth_client, lost_payload):
    lost_payload["lost_at"] = (timezone.now() + timedelta(days=1)).isoformat()
    response = auth_client.post(
        reverse("items:lost-report-list"), lost_payload, format="json"
    )

    assert response.status_code == 400
    assert "lost_at" in response.json()


def test_owner_can_edit_open_report(auth_client, lost_report):
    response = auth_client.patch(
        detail_url(lost_report),
        {"title": "Chaves do carro (atualizado)"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Chaves do carro (atualizado)"


def test_other_user_cannot_edit(other_client, lost_report):
    response = other_client.patch(
        detail_url(lost_report), {"title": "Tentativa"}, format="json"
    )

    assert response.status_code == 403


def test_owner_cancels_report(auth_client, lost_report):
    response = auth_client.post(cancel_url(lost_report))

    assert response.status_code == 200
    assert response.json()["status"] == LostReportStatus.CANCELADO
    lost_report.refresh_from_db()
    assert lost_report.status == LostReportStatus.CANCELADO


def test_cancel_twice_is_rejected(auth_client, lost_report):
    auth_client.post(cancel_url(lost_report))
    response = auth_client.post(cancel_url(lost_report))

    assert response.status_code == 400
    assert "status" in response.json()


def test_owner_cannot_edit_after_cancel(auth_client, lost_report):
    lost_report.status = LostReportStatus.CANCELADO
    lost_report.save(update_fields=["status"])

    response = auth_client.patch(
        detail_url(lost_report), {"title": "Tentativa"}, format="json"
    )

    assert response.status_code == 403


def test_admin_can_edit_after_cancel(admin_client, lost_report):
    lost_report.status = LostReportStatus.CANCELADO
    lost_report.save(update_fields=["status"])

    response = admin_client.patch(
        detail_url(lost_report), {"title": "Correção administrativa"}, format="json"
    )

    assert response.status_code == 200


def test_list_filters_and_search(auth_client, common_user, other_user, lost_report):
    LostReport.objects.create(
        owner=other_user,
        title="Relógio de pulso",
        description="Pulseira de metal.",
        category=Category.OUTROS,
        lost_at=timezone.now() - timedelta(hours=2),
        lost_location="Academia",
    )

    by_category = auth_client.get(
        reverse("items:lost-report-list"), {"category": Category.CHAVES}
    )
    assert by_category.json()["count"] == 1

    by_search = auth_client.get(
        reverse("items:lost-report-list"), {"search": "Relógio"}
    )
    assert by_search.json()["count"] == 1

    mine = auth_client.get(reverse("items:lost-report-list"), {"mine": "true"})
    assert mine.json()["count"] == 1
    assert mine.json()["results"][0]["owner"]["id"] == common_user.id


def test_delete_is_not_allowed(auth_client, lost_report):
    response = auth_client.delete(detail_url(lost_report))
    assert response.status_code == 405
