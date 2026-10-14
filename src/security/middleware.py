"""Middleware de bloqueio de IPs sinalizados pelo honeypot.

Executa cedo na pilha para barrar requisições de IPs já bloqueados antes de
qualquer processamento pesado. Para IPs confiáveis/privados (por padrão), nunca
bloqueia — evitando auto-bloqueio durante o desenvolvimento.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpResponseForbidden

from .honeypot import get_client_ip, should_block

logger = logging.getLogger("findly.security.honeypot")


class HoneypotBlockMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.HONEYPOT_ENABLED:
            ip = get_client_ip(request)
            if should_block(ip):
                logger.warning(
                    "Honeypot: requisição barrada de IP bloqueado %s (%s)",
                    ip,
                    request.path,
                )
                return HttpResponseForbidden("403 Forbidden")
        return self.get_response(request)
