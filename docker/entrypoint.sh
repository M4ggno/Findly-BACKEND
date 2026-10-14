#!/bin/sh
# =============================================================================
# Entrypoint dos containers do Findly Backend.
# Aguarda o PostgreSQL subir, aplica migrações e então executa o comando (CMD).
# =============================================================================
set -e

POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

# --- 1. Espera o PostgreSQL ficar disponível --------------------------------
if [ -n "${POSTGRES_HOST}" ]; then
    echo "[entrypoint] Aguardando PostgreSQL em ${POSTGRES_HOST}:${POSTGRES_PORT}..."
    until python - <<'PY'
import os, sys
import psycopg

try:
    psycopg.connect(
        dbname=os.environ.get("POSTGRES_DB", "findly"),
        user=os.environ.get("POSTGRES_USER", "findly"),
        password=os.environ.get("POSTGRES_PASSWORD", "findly"),
        host=os.environ.get("POSTGRES_HOST", "db"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        connect_timeout=3,
    ).close()
except Exception:
    sys.exit(1)
PY
    do
        echo "[entrypoint] PostgreSQL indisponível — aguardando 1s..."
        sleep 1
    done
    echo "[entrypoint] PostgreSQL disponível."
fi

# --- 2. Migrações (pode ser desativado com RUN_MIGRATIONS=0) ----------------
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    echo "[entrypoint] Aplicando migrações..."
    python manage.py migrate --noinput
fi

# --- 3. Arquivos estáticos (somente quando solicitado) ----------------------
if [ "${COLLECT_STATIC:-0}" = "1" ]; then
    echo "[entrypoint] Coletando arquivos estáticos..."
    python manage.py collectstatic --noinput
fi

# --- 4. Executa o comando recebido (CMD) ------------------------------------
echo "[entrypoint] Iniciando: $*"
exec "$@"
