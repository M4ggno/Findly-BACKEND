"""Ponto de entrada WSGI do Findly Backend (usado por gunicorn/uWSGI em prod)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Garante que o pacote `config` (e `apps`) sejam importáveis mesmo quando o
# processo é iniciado fora da raiz do projeto.
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
