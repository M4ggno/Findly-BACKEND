"""Testes unitários dos geradores de token (salt e expiração)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from apps.authentication.tokens import (
    EmailVerificationTokenGenerator,
    FindlyPasswordResetTokenGenerator,
    email_verification_token,
    password_reset_token,
)

pytestmark = pytest.mark.django_db


def test_tokens_de_fluxos_diferentes_sao_incompativeis(active_user):
    verify = email_verification_token.make_token(active_user)
    reset = password_reset_token.make_token(active_user)

    assert verify != reset
    assert email_verification_token.check_token(active_user, verify)
    assert not password_reset_token.check_token(active_user, verify)
    assert password_reset_token.check_token(active_user, reset)
    assert not email_verification_token.check_token(active_user, reset)


def test_token_de_verificacao_expira(monkeypatch, settings, inactive_user):
    settings.EMAIL_VERIFICATION_TIMEOUT = 60
    token = email_verification_token.make_token(inactive_user)

    future = datetime.now() + timedelta(seconds=61)
    monkeypatch.setattr(
        EmailVerificationTokenGenerator, "_now", lambda self: future, raising=False
    )

    assert email_verification_token.check_token(inactive_user, token) is False


def test_token_de_reset_expira(monkeypatch, settings, active_user):
    settings.PASSWORD_RESET_TIMEOUT = 60
    token = password_reset_token.make_token(active_user)

    future = datetime.now() + timedelta(seconds=61)
    monkeypatch.setattr(
        FindlyPasswordResetTokenGenerator, "_now", lambda self: future, raising=False
    )

    assert password_reset_token.check_token(active_user, token) is False


def test_token_valido_dentro_do_prazo(monkeypatch, settings, inactive_user):
    settings.EMAIL_VERIFICATION_TIMEOUT = 60
    token = email_verification_token.make_token(inactive_user)

    future = datetime.now() + timedelta(seconds=30)
    monkeypatch.setattr(
        EmailVerificationTokenGenerator, "_now", lambda self: future, raising=False
    )

    assert email_verification_token.check_token(inactive_user, token) is True
