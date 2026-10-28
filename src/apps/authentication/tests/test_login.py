"""Testes de login, refresh (rotação) e logout (blacklist)."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.users.models import User

pytestmark = pytest.mark.django_db

LOGIN_URL = reverse("authentication:login")
REFRESH_URL = reverse("authentication:token_refresh")
LOGOUT_URL = reverse("authentication:logout")

PASSWORD = "S3nh@Forte!2026"


def _login(client, email: str, password: str = PASSWORD):
    return client.post(
        LOGIN_URL,
        {"email": email, "password": password},
        content_type="application/json",
    )


def test_login_retorna_tokens_e_dados_do_usuario(client, active_user):
    response = _login(client, active_user.email)

    assert response.status_code == 200
    assert set(response.data) >= {"access", "refresh", "user"}
    assert response.data["user"]["id"] == active_user.pk
    assert response.data["user"]["email"] == active_user.email
    assert response.data["user"]["role"] == "common"


def test_login_rejeita_senha_incorreta(client, active_user):
    response = _login(client, active_user.email, "senha-errada")

    assert response.status_code == 401


def test_login_rejeita_usuario_nao_verificado(client, inactive_user):
    response = _login(client, inactive_user.email)

    assert response.status_code == 401


def test_refresh_rotaciona_e_invalida_o_token_anterior(client, active_user):
    tokens = _login(client, active_user.email).data

    refreshed = client.post(
        REFRESH_URL, {"refresh": tokens["refresh"]}, content_type="application/json"
    )
    assert refreshed.status_code == 200
    assert refreshed.data["access"]
    assert refreshed.data["refresh"] != tokens["refresh"]

    # O refresh antigo foi para a blacklist (BLACKLIST_AFTER_ROTATION=True).
    reused = client.post(
        REFRESH_URL, {"refresh": tokens["refresh"]}, content_type="application/json"
    )
    assert reused.status_code == 401


def test_refresh_rejeita_token_invalido(client):
    response = client.post(
        REFRESH_URL, {"refresh": "nao-e-um-token"}, content_type="application/json"
    )

    assert response.status_code == 401


def test_logout_invalida_o_refresh(client, active_user):
    tokens = _login(client, active_user.email).data
    auth = {"HTTP_AUTHORIZATION": f"Bearer {tokens['access']}"}

    logout = client.post(
        LOGOUT_URL,
        {"refresh": tokens["refresh"]},
        content_type="application/json",
        **auth,
    )
    assert logout.status_code == 200

    reused = client.post(
        REFRESH_URL, {"refresh": tokens["refresh"]}, content_type="application/json"
    )
    assert reused.status_code == 401


def test_logout_nao_permite_revogar_token_de_outro_usuario(client, active_user, db):
    outro = User.objects.create_user(
        email="outro@findly.local", password=PASSWORD, full_name="Outro"
    )

    tokens_a = _login(client, active_user.email).data
    tokens_b = _login(client, outro.email).data

    response = client.post(
        LOGOUT_URL,
        {"refresh": tokens_a["refresh"]},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {tokens_b['access']}",
    )
    assert response.status_code == 400
    assert "refresh" in response.data

    # O refresh do usuário A continua válido.
    refreshed = client.post(
        REFRESH_URL, {"refresh": tokens_a["refresh"]}, content_type="application/json"
    )
    assert refreshed.status_code == 200


def test_logout_exige_autenticacao(client, active_user):
    tokens = _login(client, active_user.email).data

    response = client.post(
        LOGOUT_URL, {"refresh": tokens["refresh"]}, content_type="application/json"
    )

    assert response.status_code == 401


def test_logout_com_refresh_invalido_retorna_400(client, active_user):
    tokens = _login(client, active_user.email).data

    response = client.post(
        LOGOUT_URL,
        {"refresh": "invalido"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
    )

    assert response.status_code == 400
    assert "refresh" in response.data
