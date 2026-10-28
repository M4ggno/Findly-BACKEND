"""Envio dos e-mails transacionais da autenticação.

Os templates ficam em ``templates/authentication/emails/`` (dentro deste app) e
são renderizados com o link do front-end já contendo ``uid`` e ``token``. Os
mesmos valores também vão no corpo do e-mail, para clientes que só consomem a
API diretamente.
"""

from __future__ import annotations

from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.users.models import User

from .tokens import email_verification_token, password_reset_token


def _url_with_token(base_url: str, uid: str, token: str) -> str:
    """Anexa ``uid``/``token`` à URL preservando query string existente."""
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode({'uid': uid, 'token': token})}"


def _send(template: str, subject: str, user: User, context: dict) -> None:
    message = render_to_string(template, context)
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def send_verification_email(user: User) -> None:
    """Envia o link para o usuário confirmar o e-mail e ativar a conta."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)

    _send(
        "authentication/emails/verify_email.txt",
        "Confirme seu e-mail — Findly",
        user,
        {
            "user": user,
            "uid": uid,
            "token": token,
            "url": _url_with_token(settings.EMAIL_VERIFICATION_URL, uid, token),
            "expires_minutes": max(1, settings.EMAIL_VERIFICATION_TIMEOUT // 60),
        },
    )


def send_password_reset_email(user: User) -> None:
    """Envia o link temporário para o usuário definir uma nova senha."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = password_reset_token.make_token(user)

    _send(
        "authentication/emails/password_reset.txt",
        "Redefinição de senha — Findly",
        user,
        {
            "user": user,
            "uid": uid,
            "token": token,
            "url": _url_with_token(settings.PASSWORD_RESET_URL, uid, token),
            "expires_minutes": max(1, settings.PASSWORD_RESET_TIMEOUT // 60),
        },
    )
