# =============================================================================
# Findly Backend — Atalhos de desenvolvimento (local + Docker)
# =============================================================================
# Ver todos os alvos:      make help
# Requer `make` (Linux/macOS/WSL/Git Bash). No Windows:
#   - via Git Bash (recomendado): "C:\Program Files\Git\bin\bash.exe"
#   - ou instale:  choco install make   /   scoop install make
# Os alvos "docker-*" exigem o daemon do Docker em execução.
# =============================================================================

COMPOSE   ?= docker compose
PY        ?= python
VENV      ?= .venv
MANAGE    := $(VENV_PY) manage.py
SERVICE   ?= web

# Detecta o interpretador do venv conforme o sistema operacional.
ifeq ($(OS),Windows_NT)
    VENV_PY := $(VENV)/Scripts/python.exe
else
    VENV_PY := $(VENV)/bin/python
endif

.DEFAULT_GOAL := help

# -----------------------------------------------------------------------------
# Ajuda
# -----------------------------------------------------------------------------
.PHONY: help
help: ## Lista os alvos disponíveis
	@echo ""
	@echo "Findly Backend - atalhos disponíveis:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""

# -----------------------------------------------------------------------------
# Ambiente local (sem Docker)
# -----------------------------------------------------------------------------
.PHONY: venv
venv: ## Cria o ambiente virtual (.venv)
	$(PY) -m venv $(VENV)

.PHONY: install
install: ## Instala as dependências de desenvolvimento no .venv
	$(VENV_PY) -m pip install --upgrade pip
	$(VENV_PY) -m pip install -r requirements-dev.txt

.PHONY: run
run: ## Roda o servidor de desenvolvimento do Django (local)
	$(MANAGE) runserver 0.0.0.0:8000

.PHONY: migrate
migrate: ## Aplica as migrações (local)
	$(MANAGE) migrate

.PHONY: makemigrations
makemigrations: ## Cria novas migrações (local)
	$(MANAGE) makemigrations

.PHONY: superuser
superuser: ## Cria um superusuário (local)
	$(MANAGE) createsuperuser

.PHONY: shell
shell: ## Abre o shell interativo do Django (local)
	$(MANAGE) shell_plus

.PHONY: check
check: ## Executa as verificações de sistema do Django (local)
	$(MANAGE) check

.PHONY: test
test: ## Roda a suíte de testes com pytest (local)
	$(VENV_PY) -m pytest

.PHONY: cov
cov: ## Roda os testes com relatório de cobertura (local)
	$(VENV_PY) -m pytest --cov=src --cov-report=term-missing

.PHONY: lint
lint: ## Analisa o código com ruff (local)
	$(VENV_PY) -m ruff check src

.PHONY: format
format: ## Formata o código com black + corrige imports com ruff (local)
	$(VENV_PY) -m black src
	$(VENV_PY) -m ruff check --fix src

.PHONY: report
report: ## Mostra os eventos capturados pelo honeypot (local)
	$(MANAGE) honeypot_report

.PHONY: gen-secret
gen-secret: ## Gera DJANGO_SECRET_KEY e DJANGO_ADMIN_URL aleatórios
	@$(VENV_PY) -c "import secrets; print('DJANGO_SECRET_KEY=' + secrets.token_urlsafe(50)); print('DJANGO_ADMIN_URL=' + secrets.token_urlsafe(18).replace('_','').replace('-','') + '/')"

.PHONY: worker
worker: ## Inicia um worker Celery (local)
	$(VENV_PY) -m celery -A config worker -l info

.PHONY: beat
beat: ## Inicia o beat Celery (local)
	$(VENV_PY) -m celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# -----------------------------------------------------------------------------
# Docker
# -----------------------------------------------------------------------------
.PHONY: up
up: ## Sobe todos os containers em background (build incluído)
	$(COMPOSE) up -d --build

.PHONY: build
build: ## (Re)constrói as imagens
	$(COMPOSE) build

.PHONY: down
down: ## Derruba e remove os containers (mantém volumes)
	$(COMPOSE) down

.PHONY: restart
restart: ## Reinicia todos os containers
	$(COMPOSE) restart

.PHONY: ps
ps: ## Lista o status dos containers
	$(COMPOSE) ps

.PHONY: logs
logs: ## Acompanha os logs de todos os serviços
	$(COMPOSE) logs -f

.PHONY: logs-web
logs-web: ## Acompanha os logs do serviço web
	$(COMPOSE) logs -f web

.PHONY: sh
sh: ## Abre um shell no container da aplicação
	$(COMPOSE) exec web bash

.PHONY: docker-migrate
docker-migrate: ## Aplica as migrações no container web
	$(COMPOSE) exec web python manage.py migrate

.PHONY: docker-makemigrations
docker-makemigrations: ## Cria migrações no container web
	$(COMPOSE) exec web python manage.py makemigrations

.PHONY: docker-superuser
docker-superuser: ## Cria superusuário no container web
	$(COMPOSE) exec web python manage.py createsuperuser

.PHONY: docker-shell
docker-shell: ## Abre o shell do Django no container web
	$(COMPOSE) exec web python manage.py shell

.PHONY: docker-test
docker-test: ## Roda os testes no container web
	$(COMPOSE) exec web python manage.py test

.PHONY: docker-report
docker-report: ## Mostra os eventos capturados pelo honeypot (container)
	$(COMPOSE) exec web python manage.py honeypot_report

.PHONY: dbshell
dbshell: ## Abre o shell do PostgreSQL via psql
	$(COMPOSE) exec db psql -U findly -d findly

.PHONY: docker-worker-logs
docker-worker-logs: ## Acompanha os logs do worker Celery
	$(COMPOSE) logs -f worker

.PHONY: docker-beat-logs
docker-beat-logs: ## Acompanha os logs do beat Celery
	$(COMPOSE) logs -f beat

.PHONY: reset
reset: ## ATENÇÃO: remove containers E volumes (apaga o banco de dados)
	$(COMPOSE) down -v

# -----------------------------------------------------------------------------
# Limpeza local
# -----------------------------------------------------------------------------
.PHONY: clean
clean: ## Remove caches Python/pytest/ruff
	@echo "Limpando caches..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache .ruff_cache .coverage htmlcov
	@echo "Pronto."
