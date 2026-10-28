"""Testes do cadastro (registro de conta)."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.users.models import User

pytestmark = pytest.mark.django_db

REGISTER_URL = reverse("authentication:register")

VALID_PAYLOAD = {
    "email": "novo@findly.local",
    "full_name": "Novo Usuário",
    "phone": "11999999999",
    "password": "S3nh@Forte!2026",
    "password_confirm": "S3nh@Forte!2026",
}


def _register(client, **overrides):
    payload = {**VALID_PAYLOAD, **overrides}
    return client.post(REGISTER_URL, payload, content_type="application/json")


def test_cadastro_cria_conta_inativa_e_envia_confirmacao(client, mailoutbox):
    response = _register(client)

    assert response.status_code == 201
    assert response.data["user"]["email"] == "novo@findly.local"
    assert response.data["user"]["is_active"] is False

    user = User.objects.get(email="novo@findly.local")
    assert user.is_active is False
    assert user.check_password("S3nh@Forte!2026")

    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["novo@findly.local"]
    assert "verificar-email" in mailoutbox[0].body
    assert "uid=" in mailoutbox[0].body and "token=" in mailoutbox[0].body


def test_cadastro_sem_verificacao_ativa_conta_direto(client, mailoutbox, settings):
    settings.AUTH_REQUIRE_EMAIL_VERIFICATION = False

    response = _register(client, email="ativo@findly.local")

    assert response.status_code == 201
    assert User.objects.get(email="ativo@findly.local").is_active is True
    assert mailoutbox == []


def test_cadastro_normaliza_email_para_minusculas(client):
    response = _register(client, email="Maiusculo@Findly.Local")

    assert response.status_code == 201
    assert User.objects.filter(email="maiusculo@findly.local").exists()


def test_cadastro_rejeita_email_duplicado(client, active_user):
    response = _register(client, email=active_user.email.upper())

    assert response.status_code == 400
    assert "email" in response.data
    assert User.objects.filter(email__iexact=active_user.email).count() == 1


def test_cadastro_rejeita_senhas_diferentes(client):
    response = _register(client, password_confirm="OutraS3nh@2026")

    assert response.status_code == 400
    assert "password_confirm" in response.data


def test_cadastro_rejeita_senha_fraca(client):
    response = _register(client, password="12345678", password_confirm="12345678")

    assert response.status_code == 400
    assert "password" in response.data
    assert not User.objects.filter(email=VALID_PAYLOAD["email"]).exists()


def test_cadastro_rejeita_senha_semelhante_ao_email(client):
    response = _register(
        client,
        email="maria.silva@findly.local",
        full_name="Maria Silva",
        password="maria.silva@findly.local",
        password_confirm="maria.silva@findly.local",
    )

    assert response.status_code == 400
    assert "password" in response.data
