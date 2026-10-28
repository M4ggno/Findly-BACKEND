"""Testes da redefinição de senha."""

from __future__ import annotations

import pytest
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.authentication.tokens import email_verification_token, password_reset_token
from apps.users.models import User

pytestmark = pytest.mark.django_db

REQUEST_URL = reverse("authentication:password_reset")
CONFIRM_URL = reverse("authentication:password_reset_confirm")
LOGIN_URL = reverse("authentication:login")
REFRESH_URL = reverse("authentication:token_refresh")

NEW_PASSWORD = "N0vaS3nh@Forte!2026"


def _confirm_payload(user, token: str, password: str = NEW_PASSWORD) -> dict:
    return {
        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        "token": token,
        "new_password": password,
        "new_password_confirm": password,
    }


def test_solicitacao_envia_email_para_conta_ativa(client, active_user, mailoutbox):
    response = client.post(
        REQUEST_URL, {"email": active_user.email}, content_type="application/json"
    )

    assert response.status_code == 202
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == [active_user.email]
    assert "redefinir-senha" in mailoutbox[0].body


def test_solicitacao_nao_revela_email_inexistente(client, mailoutbox):
    response = client.post(
        REQUEST_URL, {"email": "ninguem@findly.local"}, content_type="application/json"
    )

    assert response.status_code == 202
    assert mailoutbox == []


def test_solicitacao_ignora_conta_nao_verificada(client, inactive_user, mailoutbox):
    response = client.post(
        REQUEST_URL, {"email": inactive_user.email}, content_type="application/json"
    )

    assert response.status_code == 202
    assert mailoutbox == []


def test_confirmacao_altera_a_senha(client, active_user):
    token = password_reset_token.make_token(active_user)

    response = client.post(
        CONFIRM_URL,
        _confirm_payload(active_user, token),
        content_type="application/json",
    )

    assert response.status_code == 200
    active_user.refresh_from_db()
    assert active_user.check_password(NEW_PASSWORD)
    assert not active_user.check_password("S3nh@Forte!2026")


def test_confirmacao_rejeita_token_invalido(client, active_user):
    response = client.post(
        CONFIRM_URL,
        _confirm_payload(active_user, "token-invalido"),
        content_type="application/json",
    )

    assert response.status_code == 400
    active_user.refresh_from_db()
    assert active_user.check_password("S3nh@Forte!2026")


def test_confirmacao_rejeita_senhas_diferentes(client, active_user):
    token = password_reset_token.make_token(active_user)
    payload = _confirm_payload(active_user, token)
    payload["new_password_confirm"] = "OutraS3nh@2026"

    response = client.post(CONFIRM_URL, payload, content_type="application/json")

    assert response.status_code == 400
    assert "new_password_confirm" in response.data


def test_token_de_reset_e_de_uso_unico(client, active_user):
    token = password_reset_token.make_token(active_user)
    payload = _confirm_payload(active_user, token)

    first = client.post(CONFIRM_URL, payload, content_type="application/json")
    second = client.post(CONFIRM_URL, payload, content_type="application/json")

    assert first.status_code == 200
    assert second.status_code == 400


def test_token_de_verificacao_nao_serve_para_reset(client, active_user):
    payload = _confirm_payload(
        active_user, email_verification_token.make_token(active_user)
    )

    response = client.post(CONFIRM_URL, payload, content_type="application/json")

    assert response.status_code == 400
    active_user.refresh_from_db()
    assert active_user.check_password("S3nh@Forte!2026")


def test_reset_revoga_sessoes_anteriores(client, active_user):
    login = client.post(
        LOGIN_URL,
        {"email": active_user.email, "password": "S3nh@Forte!2026"},
        content_type="application/json",
    )
    refresh = login.data["refresh"]

    # O login atualiza ``last_login``, que faz parte do hash do token.
    active_user.refresh_from_db()
    token = password_reset_token.make_token(active_user)
    confirm = client.post(
        CONFIRM_URL,
        _confirm_payload(active_user, token),
        content_type="application/json",
    )
    assert confirm.status_code == 200

    reused = client.post(
        REFRESH_URL, {"refresh": refresh}, content_type="application/json"
    )
    assert reused.status_code == 401


def test_uid_inexistente_retorna_400(client, mailoutbox):
    response = client.post(
        CONFIRM_URL,
        {
            "uid": urlsafe_base64_encode(force_bytes(999999)),
            "token": "x",
            "new_password": NEW_PASSWORD,
            "new_password_confirm": NEW_PASSWORD,
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert not User.objects.filter(pk=999999).exists()
