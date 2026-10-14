"""Testes do honeypot e da proteção do Django Admin.

Não dependem de Redis: o honeypot degrada com segurança quando o cache está
indisponível, então os testes validam as respostas HTTP e o roteamento.
"""
from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse


@pytest.fixture
def client() -> Client:
    return Client(HTTP_HOST="localhost")


def test_admin_classico_e_honeypot(client: Client) -> None:
    response = client.get("/admin/")
    assert response.status_code == 200
    assert b"Administra" in response.content
    assert b"<form" in response.content


def test_admin_subrotas_caem_no_honeypot(client: Client) -> None:
    assert client.get("/admin/login/").status_code == 200
    assert client.get("/admin/anything/else/").status_code == 200


def test_post_de_credenciais_e_capturado(client: Client) -> None:
    response = client.post("/admin/", {"username": "root", "password": "toor"})
    assert response.status_code == 200


def test_admin_real_fica_em_caminho_secreto(client: Client) -> None:
    admin_url = reverse("admin:index")
    assert admin_url.startswith("/painel-interno/")
    # Sem sessão, o admin redireciona para a tela de login.
    assert client.get(admin_url).status_code == 302


def test_iscas_de_scanner_retornam_404(client: Client) -> None:
    for path in ("/wp-admin/", "/wp-login.php", "/phpmyadmin/", "/.env"):
        assert client.get(path).status_code == 404


def test_ip_confiavel_nunca_e_bloqueado() -> None:
    from security import honeypot

    assert honeypot.is_trusted("127.0.0.1") is True
