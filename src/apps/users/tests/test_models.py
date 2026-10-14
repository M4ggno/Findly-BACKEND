"""Testes do modelo de usuário customizado e do seu manager."""
from __future__ import annotations

import pytest

from apps.users.models import Role, User

pytestmark = pytest.mark.django_db


def test_create_user_com_email() -> None:
    user = User.objects.create_user(
        email="ana@findly.local", password="senha123", full_name="Ana Silva"
    )
    assert user.email == "ana@findly.local"
    assert user.role == Role.COMMON
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.check_password("senha123") is True
    assert user.short_name == "Ana"


def test_email_e_obrigatorio() -> None:
    with pytest.raises(ValueError):
        User.objects.create_user(email="", password="x")


def test_create_superuser_com_papeis() -> None:
    admin = User.objects.create_superuser(
        email="admin@findly.local", password="secret"
    )
    assert admin.role == Role.ADMIN
    assert admin.is_staff is True
    assert admin.is_superuser is True
    assert admin.is_admin is True


def test_username_field_e_email() -> None:
    assert User.USERNAME_FIELD == "email"


def test_short_name_usa_email_quando_sem_nome() -> None:
    user = User.objects.create_user(email="sem.nome@findly.local", password="x")
    assert user.short_name == "sem.nome@findly.local"
