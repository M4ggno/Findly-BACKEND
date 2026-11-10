"""Endpoints de saúde da aplicação.

- ``GET /health/`` — *liveness*: responde enquanto o processo web estiver vivo.
  Não toca em dependências externas, então serve para o healthcheck do Docker.
- ``GET /health/ready/`` — *readiness*: confirma banco de dados e cache. Retorna
  ``503`` quando alguma dependência está fora, para que o balanceador não envie
  tráfego para uma instância quebrada.

As rotas são públicas (sem JWT) e não passam pelo throttle do DRF.
"""

from __future__ import annotations

import logging

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)

# Chave usada no teste de leitura/escrita do cache.
CACHE_PROBE_KEY = "health:probe"


def _database_ok() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:  # noqa: BLE001 - qualquer falha significa indisponível
        logger.exception("Healthcheck: banco de dados indisponível.")
        return False
    return True


def _cache_ok() -> bool:
    try:
        cache.set(CACHE_PROBE_KEY, "ok", timeout=5)
        return cache.get(CACHE_PROBE_KEY) == "ok"
    except Exception:  # noqa: BLE001 - cache é opcional para o liveness
        logger.exception("Healthcheck: cache indisponível.")
        return False


@require_GET
def liveness(request):
    """Processo vivo: não consulta banco nem cache."""
    return JsonResponse({"status": "ok"})


@require_GET
def readiness(request):
    """Dependências prontas para receber tráfego."""
    database = _database_ok()
    cache_ok = _cache_ok()
    healthy = database and cache_ok

    payload = {
        "status": "ok" if healthy else "unavailable",
        "database": "ok" if database else "down",
        "cache": "ok" if cache_ok else "down",
    }
    return JsonResponse(payload, status=200 if healthy else 503)


__all__ = ["liveness", "readiness"]
