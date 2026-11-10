"""Tarefas assíncronas de notificação (Celery)."""

from __future__ import annotations

from celery import shared_task

from services.notification_service import NotificationMessage, deliver


@shared_task(name="notifications.send")
def send_notification(payload: dict) -> None:
    """Entrega uma mensagem serializada (agendada por ``dispatch``).

    O ``deliver`` já isola falhas por canal; a task existe para tirar o envio
    do processo web e permitir retry/observabilidade no worker.
    """
    deliver(NotificationMessage(**payload))


__all__ = ["send_notification"]
