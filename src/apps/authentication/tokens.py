"""Tokens de uso único para verificação de e-mail e redefinição de senha.

Os dois fluxos derivam de ``PasswordResetTokenGenerator`` do Django, mas usam
``key_salt`` distintos: um token emitido para verificar o e-mail **não** é aceito
no fluxo de redefinição de senha (e vice-versa).

A expiração é lida de ``settings`` a cada validação (e não fixada no import),
o que mantém os geradores testáveis com ``override_settings``.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.crypto import constant_time_compare
from django.utils.http import base36_to_int


class _TimedTokenGenerator(PasswordResetTokenGenerator):
    """Gerador de token com expiração configurável por fluxo."""

    timeout_setting = "PASSWORD_RESET_TIMEOUT"

    @property
    def timeout(self) -> int:
        return int(getattr(settings, self.timeout_setting))

    def check_token(self, user, token: str) -> bool:
        """Valida o token aplicando o timeout do fluxo.

        Espelha ``PasswordResetTokenGenerator.check_token`` (Django 5.2), que
        aceita rotação de ``SECRET_KEY`` via ``secret``/``secret_fallbacks``,
        trocando apenas ``settings.PASSWORD_RESET_TIMEOUT`` por ``self.timeout``.
        """
        if not (user and token):
            return False

        try:
            ts_b36, _ = token.split("-")
        except ValueError:
            return False

        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        for secret in [self.secret, *self.secret_fallbacks]:
            if constant_time_compare(
                self._make_token_with_timestamp(user, ts, secret), token
            ):
                break
        else:
            return False

        if (self._num_seconds(self._now()) - ts) > self.timeout:
            return False

        return True


class EmailVerificationTokenGenerator(_TimedTokenGenerator):
    """Token de confirmação de e-mail (uso único)."""

    key_salt = "apps.authentication.tokens.email_verification"
    timeout_setting = "EMAIL_VERIFICATION_TIMEOUT"

    def _make_hash_value(self, user, timestamp: int) -> str:
        # Incluir ``is_active`` invalida o token depois da ativação.
        return f"{user.pk}{user.password}{timestamp}{user.email}{user.is_active}"


class FindlyPasswordResetTokenGenerator(_TimedTokenGenerator):
    """Token de redefinição de senha (independente do de verificação)."""

    key_salt = "apps.authentication.tokens.password_reset"


email_verification_token = EmailVerificationTokenGenerator()
password_reset_token = FindlyPasswordResetTokenGenerator()
