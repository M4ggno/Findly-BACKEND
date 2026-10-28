"""Testes da verificação de e-mail."""

from __future__ import annotations

import pytest
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.authentication.tokens import email_verification_token, password_reset_token
from apps.users.models import User

pytestmark = pytest.mark.django_db

VERIFY_URL = reverse("authentication:verify_email")
RESEND_URL = reverse("authentication:resend_verification")


def _payload(user) -> dict:
    return {
        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        "token": email_verification_token.make_token(user),
    }


def test_verificacao_ativa_a_conta(client, inactive_user):
    response = client.post(
        VERIFY_URL, _payload(inactive_user), content_type="application/json"
    )

    assert response.status_code == 200
    inactive_user.refresh_from_db()
    assert inactive_user.is_active is True


def test_token_de_verificacao_nao_pode_ser_reutilizado(client, inactive_user):
    payload = _payload(inactive_user)

    first = client.post(VERIFY_URL, payload, content_type="application/json")
    second = client.post(VERIFY_URL, payload, content_type="application/json")

    assert first.status_code == 200
    assert second.status_code == 400


def test_verificacao_rejeita_token_invalido(client, inactive_user):
    payload = {**_payload(inactive_user), "token": "token-invalido"}

    response = client.post(VERIFY_URL, payload, content_type="application/json")

    assert response.status_code == 400
    inactive_user.refresh_from_db()
    assert inactive_user.is_active is False


def test_verificacao_rejeita_uid_invalido(client):
    response = client.post(
        VERIFY_URL,
        {"uid": "***", "token": "x"},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_reenvio_envia_email_para_conta_inativa(client, inactive_user, mailoutbox):
    response = client.post(
        RESEND_URL, {"email": inactive_user.email}, content_type="application/json"
    )

    assert response.status_code == 202
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == [inactive_user.email]


def test_reenvio_nao_envia_para_conta_ativa(client, active_user, mailoutbox):
    response = client.post(
        RESEND_URL, {"email": active_user.email}, content_type="application/json"
    )

    assert response.status_code == 202
    assert mailoutbox == []


def test_reenvio_nao_revela_email_inexistente(client, mailoutbox):
    response = client.post(
        RESEND_URL, {"email": "ninguem@findly.local"}, content_type="application/json"
    )

    assert response.status_code == 202
    assert mailoutbox == []


def test_token_de_reset_nao_serve_para_verificar_email(client, inactive_user):
    payload = {
        "uid": urlsafe_base64_encode(force_bytes(inactive_user.pk)),
        "token": password_reset_token.make_token(inactive_user),
    }

    response = client.post(VERIFY_URL, payload, content_type="application/json")

    assert response.status_code == 400
    assert not User.objects.get(pk=inactive_user.pk).is_active
