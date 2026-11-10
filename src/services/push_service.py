"""Envio de Web Push (VAPID) com tratamento de inscrição expirada.

O ``pywebpush`` é importado de forma tolerante: se a dependência não estiver
instalada, o serviço apenas registra no log e devolve ``skipped``, sem quebrar
o fluxo de negócio que originou a notificação.
"""

from __future__ import annotations

import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

try:  # pragma: no cover - depende do ambiente
    from pywebpush import WebPushException, webpush
except ImportError:  # pragma: no cover - fallback sem a dependência
    webpush = None

    class WebPushException(Exception):
        """Erro de entrega do Web Push (fallback sem ``pywebpush``)."""

        def __init__(self, message: str = "", response=None) -> None:
            super().__init__(message)
            self.response = response


# Resultados possíveis de uma tentativa de entrega.
SENT = "sent"
EXPIRED = "expired"
FAILED = "failed"
SKIPPED = "skipped"

# Códigos que significam "esta inscrição não existe mais".
EXPIRED_STATUS_CODES = frozenset({404, 410})


def is_configured() -> bool:
    """O canal está habilitado e com o par VAPID completo?"""
    return bool(
        settings.NOTIFICATIONS_PUSH_ENABLED
        and settings.VAPID_PRIVATE_KEY
        and settings.VAPID_PUBLIC_KEY
    )


def send(subscription_info: dict, payload: dict) -> str:
    """Entrega uma notificação a uma inscrição.

    Devolve ``sent``, ``expired`` (inscrição deve ser desativada), ``failed``
    (erro transitório, mantém a inscrição) ou ``skipped`` (canal desligado).
    """
    if webpush is None:
        logger.warning("pywebpush não instalado; push ignorado.")
        return SKIPPED

    if not is_configured():
        logger.warning(
            "Push habilitado sem VAPID_PUBLIC_KEY/VAPID_PRIVATE_KEY; ignorado."
        )
        return SKIPPED

    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{settings.VAPID_ADMIN_EMAIL}"},
            timeout=10,
        )
    except WebPushException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code in EXPIRED_STATUS_CODES:
            logger.info("Inscrição de push expirada (HTTP %s).", status_code)
            return EXPIRED
        logger.exception("Falha ao entregar push (HTTP %s).", status_code)
        return FAILED
    except Exception:  # noqa: BLE001 - notificação nunca derruba o negócio
        logger.exception("Falha inesperada ao entregar push.")
        return FAILED

    return SENT


__all__ = [
    "EXPIRED",
    "FAILED",
    "SENT",
    "SKIPPED",
    "WebPushException",
    "is_configured",
    "send",
]
