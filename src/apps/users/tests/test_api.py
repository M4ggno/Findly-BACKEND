"""Testes da API de usuários (perfil e gestão administrativa)."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.users.models import Role, User

pytestmark = pytest.mark.django_db

ME_URL = reverse("users:me")
LIST_URL = reverse("users:user-list")


def _detail_url(user: User) -> str:
    return reverse("users:user-detail", args=[user.pk])


def _login_token(user: User) -> str:
    """Gera um access token real (sem passar pelo throttle do login)."""
    from rest_framework_simplejwt.tokens import RefreshToken

    return str(RefreshToken.for_user(user).access_token)


# ---------------------------------------------------------------------------
# Perfil (/api/users/me/)
# ---------------------------------------------------------------------------
def test_me_exige_autenticacao(api_client):
    response = api_client.get(ME_URL)

    assert response.status_code == 401


def test_me_retorna_apenas_o_proprio_usuario(auth_client, common_user, other_user):
    response = auth_client.get(ME_URL)

    assert response.status_code == 200
    assert response.data["id"] == common_user.pk
    assert response.data["email"] == common_user.email
    assert response.data["role"] == Role.COMMON


def test_me_aceita_token_jwt_real(api_client, common_user):
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_login_token(common_user)}")

    response = api_client.get(ME_URL)

    assert response.status_code == 200
    assert response.data["email"] == common_user.email


def test_me_atualiza_dados_cadastrais(auth_client, common_user):
    response = auth_client.patch(
        ME_URL,
        {"full_name": "Nome Atualizado", "phone": "11988887777"},
        format="json",
    )

    assert response.status_code == 200
    common_user.refresh_from_db()
    assert common_user.full_name == "Nome Atualizado"
    assert common_user.phone == "11988887777"


def test_me_nao_permite_alterar_papel_ou_status(auth_client, common_user):
    response = auth_client.patch(
        ME_URL,
        {"role": Role.ADMIN, "is_active": False, "email": "invasor@findly.local"},
        format="json",
    )

    assert response.status_code == 200
    common_user.refresh_from_db()
    assert common_user.role == Role.COMMON
    assert common_user.is_active is True
    assert common_user.email == "comum@findly.local"


def test_me_rejeita_payload_invalido(auth_client):
    response = auth_client.patch(ME_URL, {"phone": "x" * 50}, format="json")

    assert response.status_code == 400
    assert "phone" in response.data


# ---------------------------------------------------------------------------
# Listagem / detalhe (administração)
# ---------------------------------------------------------------------------
def test_listagem_exige_papel_admin(api_client, common_user, operator_user):
    for user in (common_user, operator_user):
        api_client.force_authenticate(user=user)
        response = api_client.get(LIST_URL)
        assert response.status_code == 403


def test_admin_lista_usuarios_paginados(
    api_client, admin_user, common_user, other_user
):
    api_client.force_authenticate(user=admin_user)

    response = api_client.get(LIST_URL)

    assert response.status_code == 200
    assert response.data["count"] == 3
    assert len(response.data["results"]) == 3
    emails = {row["email"] for row in response.data["results"]}
    assert emails == {admin_user.email, common_user.email, other_user.email}


def test_listagem_filtra_por_papel_e_status(
    api_client, admin_user, common_user, other_user
):
    api_client.force_authenticate(user=admin_user)

    by_role = api_client.get(LIST_URL, {"role": Role.OPERATOR})
    assert by_role.status_code == 200
    assert {row["email"] for row in by_role.data["results"]} == {"outro@findly.local"}

    by_status = api_client.get(LIST_URL, {"is_active": "false"})
    assert by_status.status_code == 200
    assert by_status.data["count"] == 0


def test_listagem_busca_por_nome(api_client, admin_user, common_user):
    api_client.force_authenticate(user=admin_user)

    response = api_client.get(LIST_URL, {"search": "Comum"})

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["email"] == common_user.email


def test_admin_detalha_usuario(api_client, admin_user, common_user):
    api_client.force_authenticate(user=admin_user)

    response = api_client.get(_detail_url(common_user))

    assert response.status_code == 200
    assert response.data["email"] == common_user.email


def test_admin_recebe_404_para_usuario_inexistente(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)

    response = api_client.get(reverse("users:user-detail", args=[999999]))

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Edição administrativa
# ---------------------------------------------------------------------------
def test_admin_promove_usuario(api_client, admin_user, common_user):
    api_client.force_authenticate(user=admin_user)

    response = api_client.patch(
        _detail_url(common_user), {"role": Role.OPERATOR}, format="json"
    )

    assert response.status_code == 200
    common_user.refresh_from_db()
    assert common_user.role == Role.OPERATOR


def test_admin_desativa_usuario_e_revoga_sessoes(api_client, admin_user, common_user):
    from rest_framework_simplejwt.token_blacklist.models import (
        BlacklistedToken,
        OutstandingToken,
    )
    from rest_framework_simplejwt.tokens import RefreshToken

    RefreshToken.for_user(common_user)
    api_client.force_authenticate(user=admin_user)

    response = api_client.patch(
        _detail_url(common_user), {"is_active": False}, format="json"
    )

    assert response.status_code == 200
    common_user.refresh_from_db()
    assert common_user.is_active is False

    outstanding = OutstandingToken.objects.filter(user=common_user)
    assert outstanding.exists()
    assert BlacklistedToken.objects.filter(token__in=outstanding).count() == (
        outstanding.count()
    )


def test_usuario_desativado_perde_acesso_com_token_antigo(
    api_client, admin_user, common_user
):
    token = _login_token(common_user)
    api_client.force_authenticate(user=admin_user)
    api_client.patch(_detail_url(common_user), {"is_active": False}, format="json")

    api_client.force_authenticate(user=None)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.get(ME_URL)

    assert response.status_code == 401


def test_admin_nao_edita_o_proprio_registro(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)

    response = api_client.patch(
        _detail_url(admin_user), {"role": Role.COMMON}, format="json"
    )

    assert response.status_code == 400
    admin_user.refresh_from_db()
    assert admin_user.role == Role.ADMIN


def test_superusuario_nao_perde_papel_admin(api_client, superuser):
    api_client.force_authenticate(user=superuser)
    outro_admin = User.objects.create_user(
        email="admin2@findly.local", password="S3nh@Forte!2026", role=Role.ADMIN
    )
    # A proteção vale mesmo quando outro admin tenta rebaixar o superusuário.
    api_client.force_authenticate(user=outro_admin)

    response = api_client.patch(
        _detail_url(superuser), {"role": Role.COMMON}, format="json"
    )

    assert response.status_code == 400
    assert "role" in response.data
    superuser.refresh_from_db()
    assert superuser.role == Role.ADMIN
    assert superuser.is_superuser is True


def test_edicao_nao_permite_trocar_email(api_client, admin_user, common_user):
    api_client.force_authenticate(user=admin_user)

    response = api_client.patch(
        _detail_url(common_user), {"email": "novo@findly.local"}, format="json"
    )

    assert response.status_code == 200
    common_user.refresh_from_db()
    assert common_user.email == "comum@findly.local"


def test_viewset_nao_expoe_criacao_nem_exclusao(api_client, admin_user, common_user):
    api_client.force_authenticate(user=admin_user)

    created = api_client.post(LIST_URL, {"email": "x@findly.local"}, format="json")
    deleted = api_client.delete(_detail_url(common_user))

    assert created.status_code == 405
    assert deleted.status_code == 405
