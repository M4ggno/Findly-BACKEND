"""Pacote de configuração global do Findly Backend (settings, urls, wsgi, asgi).

A aplicação Celery é criada aqui para que seja carregada sempre que o Django
iniciar, garantindo que as ``@shared_task`` sejam registradas.
"""
from __future__ import annotations

from .celery import app as celery_app

__all__ = ("celery_app",)
