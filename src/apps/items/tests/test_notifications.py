"""Testes do serviço de notificações aplicado ao app de itens (matching)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.items.models import (
    Category,
    FoundItem,
    ItemStatus,
    LostReport,
    LostReportStatus,
)
from services import notification_service

pytestmark = pytest.mark.django_db


def _make_lost_report(owner, **overrides) -> LostReport:
    data = {
        "owner": owner,
        "title": "Carteira de couro preta",
        "description": "Carteira com documentos e cartões.",
        "category": Category.CARTEIRAS,
        "lost_at": timezone.now() - timedelta(days=1),
        "lost_location": "Recepção do prédio A",
    }
    data.update(overrides)
    return LostReport.objects.create(**data)


def _found_payload(**overrides) -> dict:
    data = {
        "title": "Carteira preta encontrada",
        "description": "Carteira de couro com documentos.",
        "category": Category.CARTEIRAS,
        "found_at": (timezone.now() - timedelta(hours=2)).isoformat(),
        "found_location": "Recepção do prédio A",
    }
    data.update(overrides)
    return data


def test_new_found_item_notifies_matching_lost_report(
    auth_client, other_user, mailoutbox, django_capture_on_commit_callbacks
):
    lost = _make_lost_report(other_user)

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.post(
            reverse("items:found-item-list"), _found_payload(), format="json"
        )

    assert response.status_code == 201
    assert len(mailoutbox) == 1
    message = mailoutbox[0]
    assert message.to == [other_user.email]
    assert "Carteira preta encontrada" in message.body
    assert lost.public_code in message.body


def test_new_found_item_without_match_does_not_notify(
    auth_client, mailoutbox, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.post(
            reverse("items:found-item-list"),
            _found_payload(category=Category.ELETRONICOS),
            format="json",
        )

    assert response.status_code == 201
    assert mailoutbox == []


def test_match_requires_shared_keywords(
    auth_client, other_user, mailoutbox, django_capture_on_commit_callbacks
):
    _make_lost_report(
        other_user,
        title="Bolsa marrom",
        description="Bolsa grande de viagem.",
    )

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.post(
            reverse("items:found-item-list"), _found_payload(), format="json"
        )

    assert response.status_code == 201
    assert mailoutbox == []


def test_match_respects_the_configured_window(
    auth_client, other_user, mailoutbox, django_capture_on_commit_callbacks
):
    _make_lost_report(
        other_user,
        lost_at=timezone.now() - timedelta(days=40),
    )

    with django_capture_on_commit_callbacks(execute=True):
        auth_client.post(
            reverse("items:found-item-list"), _found_payload(), format="json"
        )

    assert mailoutbox == []


def test_match_ignores_closed_lost_reports(
    auth_client, other_user, mailoutbox, django_capture_on_commit_callbacks
):
    _make_lost_report(other_user, status=LostReportStatus.CANCELADO)

    with django_capture_on_commit_callbacks(execute=True):
        auth_client.post(
            reverse("items:found-item-list"), _found_payload(), format="json"
        )

    assert mailoutbox == []


def test_new_lost_report_notifies_owner_of_matching_found_item(
    other_client, other_user, found_item, mailoutbox, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        response = other_client.post(
            reverse("items:lost-report-list"),
            {
                "title": "Carteira de couro",
                "description": "Carteira com documentos importantes.",
                "category": Category.CARTEIRAS,
                "lost_at": (timezone.now() - timedelta(days=2)).isoformat(),
                "lost_location": "Recepção do prédio A",
            },
            format="json",
        )

    assert response.status_code == 201
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == [other_user.email]
    assert found_item.public_code in mailoutbox[0].body


def test_lost_report_without_match_does_not_notify(
    other_client, mailoutbox, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        response = other_client.post(
            reverse("items:lost-report-list"),
            {
                "title": "Chaves do carro",
                "description": "Chave com controle remoto.",
                "category": Category.CHAVES,
                "lost_at": (timezone.now() - timedelta(hours=4)).isoformat(),
                "lost_location": "Estacionamento",
            },
            format="json",
        )

    assert response.status_code == 201
    assert mailoutbox == []


def test_lost_report_ignores_terminal_found_items(
    other_client, found_item, mailoutbox, django_capture_on_commit_callbacks
):
    found_item.status = ItemStatus.DEVOLVIDO
    found_item.save(update_fields=["status"])

    with django_capture_on_commit_callbacks(execute=True):
        other_client.post(
            reverse("items:lost-report-list"),
            {
                "title": "Carteira de couro",
                "description": "Carteira com documentos.",
                "category": Category.CARTEIRAS,
                "lost_at": (timezone.now() - timedelta(days=2)).isoformat(),
                "lost_location": "Recepção do prédio A",
            },
            format="json",
        )

    assert mailoutbox == []


def test_lost_report_does_not_match_item_found_before_the_loss(
    other_client, other_user, mailoutbox, django_capture_on_commit_callbacks
):
    FoundItem.objects.create(
        reported_by=other_user,
        title="Carteira de couro",
        description="Carteira com documentos.",
        category=Category.CARTEIRAS,
        found_at=timezone.now() - timedelta(days=3),
        found_location="Recepção do prédio A",
    )

    with django_capture_on_commit_callbacks(execute=True):
        other_client.post(
            reverse("items:lost-report-list"),
            {
                "title": "Carteira de couro",
                "description": "Carteira com documentos.",
                "category": Category.CARTEIRAS,
                "lost_at": (timezone.now() - timedelta(days=1)).isoformat(),
                "lost_location": "Recepção do prédio A",
            },
            format="json",
        )

    assert mailoutbox == []


def test_email_failure_does_not_break_item_creation(
    auth_client, other_user, monkeypatch, django_capture_on_commit_callbacks
):
    _make_lost_report(other_user)

    def boom(*args, **kwargs):
        raise RuntimeError("SMTP fora do ar")

    monkeypatch.setattr(notification_service, "send_mail", boom)

    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.post(
            reverse("items:found-item-list"), _found_payload(), format="json"
        )

    assert response.status_code == 201


def test_keywords_normalizes_accents_and_ignores_stopwords():
    assert notification_service.keywords("Carteira de couro") == {
        "carteira",
        "couro",
    }
    assert notification_service.keywords("Óculos de grau") == {"oculos", "grau"}
    assert notification_service.keywords("de do da para") == set()
