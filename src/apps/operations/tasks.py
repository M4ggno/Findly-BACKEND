"""Tarefas assíncronas/agendadas do app de operações.

- ``cleanup_expired_withdrawal_qrs``: remove os arquivos PNG de QR Codes de
  retirada vencidos, preservando o registro (e a trilha de auditoria).
"""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import WithdrawalAuthority

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_withdrawal_qrs(retention_days: int | None = None) -> dict[str, int]:
    """Apaga o PNG de QR Codes expirados há mais de ``retention_days`` dias.

    O registro de ``WithdrawalAuthority`` é mantido (histórico/auditoria); só o
    arquivo em ``media/qrcodes/withdrawals/`` é removido e o campo é limpo.
    """
    window = (
        settings.WITHDRAWAL_QR_RETENTION_DAYS
        if retention_days is None
        else retention_days
    )
    cutoff = timezone.now() - timedelta(days=window)

    authorities = list(
        WithdrawalAuthority.objects.filter(expires_at__lt=cutoff)
        .exclude(qr_image="")
        .only("pk", "qr_image")
    )

    cleaned = 0
    for authority in authorities:
        if authority.qr_image:
            authority.qr_image.delete(save=False)
        WithdrawalAuthority.objects.filter(pk=authority.pk).update(qr_image="")
        cleaned += 1

    if cleaned:
        logger.info("Limpeza de QR: %s arquivo(s) removido(s).", cleaned)
    return {"cleaned": cleaned}
