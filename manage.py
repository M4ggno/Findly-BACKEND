#!/usr/bin/env python
"""Utilitário de linha de comando do Django para tarefas administrativas.

O código-fonte do projeto fica dentro de ``src/`` (padrão ``src layout``). Este
script garante que ``src/`` esteja no ``sys.path`` para que os módulos
``config``, ``apps`` e ``services`` sejam importáveis.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent
    src_dir = project_root / "src"

    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Não foi possível importar o Django. Verifique se o ambiente "
            "virtual está ativo e se as dependências foram instaladas "
            "(pip install -r requirements-dev.txt)."
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
