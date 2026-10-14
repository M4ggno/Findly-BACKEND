"""Rotas das armadilhas (honeypot).

Incluído na raiz do projeto **antes** do Django Admin real, de modo que o
clássico ``/admin/`` caia sempre na isca.
"""
from __future__ import annotations

import re

from django.conf import settings
from django.urls import re_path

from . import honeypot

urlpatterns = []

if settings.HONEYPOT_ENABLED:
    # Armadilha principal: qualquer acesso ao clássico /admin (e subrotas),
    # incluindo tentativas de login (POST).
    urlpatterns.append(
        re_path(
            r"^admin(?:/.*)?$",
            honeypot.admin_honeypot_view,
            name="admin-honeypot",
        )
    )

    # Iscas adicionais normalmente varridas por scanners automatizados.
    for _decoy in settings.HONEYPOT_EXTRA_PATHS:
        urlpatterns.append(
            re_path(
                rf"^{re.escape(_decoy)}/?$",
                honeypot.scanner_honeypot_view,
                name=f"honeypot-{_decoy}",
            )
        )
