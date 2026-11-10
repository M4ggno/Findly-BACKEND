"""Registra as tarefas periódicas do Findly no django-celery-beat.

O ``beat`` usa ``DatabaseScheduler`` (ver ``docker-compose.yml``), então o
agendamento vive no banco. Este comando é idempotente: pode rodar em todo deploy
para criar/atualizar as tarefas sem duplicá-las.

Uso::

    python manage.py setup_periodic_tasks
"""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask

# (nome, task, hora, minuto) — horários no fuso de ``settings.TIME_ZONE``.
PERIODIC_TASKS: tuple[tuple[str, str, str, str], ...] = (
    (
        "Findly — expirar itens achados",
        "apps.items.tasks.expire_found_items",
        "3",
        "0",
    ),
    (
        "Findly — expirar alertas de perda",
        "apps.items.tasks.expire_lost_reports",
        "3",
        "15",
    ),
    (
        "Findly — limpar QR de retirada vencidos",
        "apps.operations.tasks.cleanup_expired_withdrawal_qrs",
        "3",
        "30",
    ),
)


class Command(BaseCommand):
    help = "Cria/atualiza as tarefas periódicas do Findly no django-celery-beat."

    def handle(self, *args, **options):
        created = updated = 0

        for name, task, hour, minute in PERIODIC_TASKS:
            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=minute,
                hour=hour,
                day_of_week="*",
                day_of_month="*",
                month_of_year="*",
                timezone=settings.TIME_ZONE,
            )
            _, was_created = PeriodicTask.objects.update_or_create(
                name=name,
                defaults={
                    "task": task,
                    "crontab": schedule,
                    "interval": None,
                    "enabled": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Tarefas periódicas prontas: {created} criada(s), {updated} atualizada(s)."
            )
        )
