"""Configuração da aplicação Celery do Findly Backend.

O Celery é usado para tarefas assíncronas e agendadas (ex.: disparo de
notificações, limpeza/expiração de itens e processamento de mídia). O broker e
o result backend são o Redis (ver variáveis CELERY_* em ``settings.py``).
"""
from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("findly")

# Lê a configuração a partir das variáveis CELERY_* do settings do Django.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Descobre automaticamente tarefas em `tasks.py` de cada app instalado.
app.autodiscover_tasks()
