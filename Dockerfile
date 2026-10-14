# =============================================================================
# Findly Backend — Imagem da aplicação (Django + Python)
# =============================================================================
# Base alinhada ao README (Python 3.11+). O código vive em /app/src e o
# PYTHONPATH aponta para /app/src (pacotes `config`, `apps`, `services`).
# =============================================================================
FROM python:3.11-slim

# --- Variáveis de ambiente do interpretador ---------------------------------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# --- Dependências de sistema ------------------------------------------------
# libpq5: cliente PostgreSQL | curl: healthcheck | build-essential+libpq-dev: build
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# --- Dependências Python ----------------------------------------------------
# Copiadas antes do código para aproveitar o cache de camadas do Docker.
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# --- Código da aplicação ----------------------------------------------------
COPY . .

RUN chmod +x /app/docker/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]

# Em produção o padrão é o gunicorn. Em desenvolvimento o docker-compose
# sobrescreve o CMD para usar o runserver.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
