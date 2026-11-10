# 📝 LOGS — Findly Backend

Diário de desenvolvimento do backend do **Findly**. Registra, em ordem
cronológica, tudo que foi feito, decidido e validado no projeto — incluindo
comandos executados, arquivos criados e pendências.

> Este arquivo é um **documento vivo**: novas entradas devem ser adicionadas ao
> final, sem apagar o histórico.

---

## 🗓️ 2026-10-14 — Bootstrap do projeto (configurações iniciais)

### 🎯 Objetivo da tarefa
Iniciar a criação do projeto realizando **apenas a base/infraestrutura**:
ambiente virtual, instalação do Django, `Makefile` de atalhos (incluindo Docker),
configuração dos containers e o esqueleto do projeto Django. Os apps de domínio,
serializers, viewsets e regras de negócio ficam para a **próxima etapa**.

---

### 🔍 1. Diagnóstico do ambiente (softwares detectados)

| Ferramenta | Versão detectada | Observação |
| :--- | :--- | :--- |
| Python | **3.14.7** | Única versão instalada (via `py`). `python3` não existe no PATH. |
| pip / venv | via `python -m venv` | OK |
| Docker | **29.8.0** | CLI instalado |
| Docker Compose | **v5.5.1** | OK |
| Git | 2.55.0 (windows) | OK |
| GNU Make | **não instalado** | Ver observação na seção 8. |
| Docker daemon | **parado** | Docker Desktop não estava em execução (necessário iniciar para subir containers). |

---

### 🧠 2. Análise do README e lacunas identificadas

O README descreve uma arquitetura em camadas com Django + DRF, PostgreSQL,
JWT, Pillow, QR Code, auditoria e Docker. Durante a análise, identificamos
componentes **não citados explicitamente** no README, mas **necessários** para
cumprir requisitos que o próprio README define:

| Lacuna | Por que é necessária (justificativa no contexto do Findly) | Decisão |
| :--- | :--- | :--- |
| **Redis** | O README cita *Rate Limiting*, um **Serviço de Notificações** e URL com `static_volume`. O Redis é usado como: (1) backend de **cache** (2) backend de **throttling** confiável do DRF e (3) **broker/result backend** do Celery. | ✅ **Incluído** (`redis` + `django-redis`) |
| **Celery (+ Beat)** | As notificações (e-mail/push) e o processamento pesado (compressão de fotos, geração de QR Code) **não podem bloquear a request HTTP**. Além disso, a máquina de estados do item possui o status `[EXPIRADO / ENCAMINHADO]`, que exige **tarefas agendadas (periódicas)**. | ✅ **Incluído** (`celery`, `django-celery-beat`, `django-celery-results`) |
| **Variáveis de ambiente** | Boas práticas de 12-factor; necessário para separar dev/prod (secret key, DB, Redis). | ✅ **Incluído** (`django-environ`) |
| **CORS** | O backend será consumido por front-end web e app mobile em domínios distintos. | ✅ **Incluído** (`django-cors-headers`) |
| **Documentação de API** | O README cita `static_volume` para "Swagger/OpenAPI". | ✅ **Incluído** (`drf-spectacular`) |
| **Filtros/ordenação/paginação** | Padrão esperado em APIs REST de listagem. | ✅ **Incluído** (`django-filter` + paginação do DRF) |
| **Driver PostgreSQL** | Django não fala com Postgres nativamente. | ✅ **Incluído** (`psycopg[binary]` — Psycopg 3) |
| **Servidor de produção** | O container precisa servir WSGI em produção. | ✅ **Incluído** (`gunicorn`) |

> **Conclusão:** Redis e Celery **são necessários** (não apenas "legais de ter")
> porque o desenho do sistema exige notificações assíncronas, processamento de
> mídia e expiração automática de itens. Foram adicionados à stack e à
> orquestração Docker (`redis`, `worker`, `beat`).

**Itens deliberadamente NÃO incluídos nesta etapa:** model de usuário customizado
e os apps de domínio (ficam para a próxima fase). ⚠️ Ver **pendência crítica** na
seção 9.

---

### 📦 3. Stack final instalada (`.venv`)

Ambiente virtual criado em `.venv/` com **Python 3.14.7**. Pacotes principais
(pinados em `requirements.txt` / `requirements-dev.txt`):

**Runtime / base**
- Django **5.2.18** (linha 5.x, LTS)
- djangorestframework **3.18.3**
- djangorestframework-simplejwt **5.5.1**
- drf-spectacular **0.30.0**
- django-filter **26.2**
- django-cors-headers **4.9.0**
- psycopg[binary] **3.3.6**
- django-environ **0.14.0**
- Pillow **12.3.0**
- qrcode[pil] **8.2**
- django-simple-history **3.13.0**
- redis **8.1.0**
- celery **5.6.3**
- django-redis **7.0.0**
- django-celery-beat **2.9.0**
- django-celery-results **2.6.0**
- gunicorn **26.2.0**

**Desenvolvimento**
- pytest **9.1.1** · pytest-django **4.14.0** · pytest-cov **7.1.0**
- ruff **0.17.0** · black **26.10.1**
- ipython **9.17.1** · django-extensions **4.1**

---

### 📁 4. Arquivos e diretórios criados

```text
Findly-BACKEND/
├── .dockerignore            # arquivos ignorados no build da imagem
├── .env                     # variáveis de ambiente locais (gitignored)
├── .env.example             # modelo versionável das variáveis
├── .gitignore               # ignore de Python/Django/Docker
├── Dockerfile               # imagem Django (python:3.11-slim) + entrypoint
├── docker-compose.yml       # db, redis, web, worker, beat
├── Makefile                 # atalhos local + Docker
├── LOGS.md                  # este diário
├── README.md                # (existente) System Design oficial
├── manage.py                # entrypoint Django (adiciona src/ ao sys.path)
├── pyproject.toml           # config de ruff, black e pytest
├── requirements.txt         # dependências de runtime
├── requirements-dev.txt     # dependências de desenvolvimento
├── docker/
│   └── entrypoint.sh        # espera o DB, migra e executa o CMD
├── docs/
│   └── .gitkeep             # pasta para o diagrama de arquitetura
└── src/
    ├── apps/__init__.py     # pacote dos apps de domínio (a implementar)
    ├── services/__init__.py # pacote da camada de serviços (a implementar)
    └── config/
        ├── __init__.py      # exporta a app Celery
        ├── settings.py      # configuração global (env-driven)
        ├── urls.py          # rotas raiz + Swagger/Redoc
        ├── wsgi.py          # entrada WSGI (gunicorn)
        ├── asgi.py          # entrada ASGI
        └── celery.py        # instância do Celery
```

**Padrão adotado:** *src layout* — todo o código vive em `src/`, que é adicionado
ao `PYTHONPATH` (via `manage.py`, `wsgi.py`/`asgi.py` e variável `PYTHONPATH=/app/src`
no `Dockerfile`).

---

### ⚙️ 5. Decisões de configuração relevantes (`settings.py`)

- **Ambiente 100% dirigido por variáveis** (`django-environ`), com `.env` local e
  apoio a `DATABASE_URL`.
- **Banco:** PostgreSQL via `DATABASE_URL` **ou** variáveis `POSTGRES_*` (permite
  rodar local em `localhost` e no Docker em `db` sem mexer no código).
- **DRF:** autenticação padrão **JWT** (`simplejwt`) com *refresh rotativo* e
  *blacklist*; paginação de 20 itens; throttling (anônimo/usuário) apoiado no Redis.
- **Cache:** Redis (`django-redis`), prefixo `findly`.
- **Celery:** broker no DB `1` e result backend no DB `2` do Redis; scheduler do
  `beat` no banco (`django_celery_beat`) para permitir agendamento via Admin.
- **OpenAPI:** `drf-spectacular` em `/api/schema/`, Swagger em `/api/docs/` e
  ReDoc em `/api/redoc/`.
- **Auditoria:** `django-simple-history` + middleware de histórico já ativos.
- **Endurecimento de produção:** HSTS/SSL/cookies seguros habilitados
  automaticamente quando `DJANGO_DEBUG=False`.
- **Fuso/hora:** `America/Sao_Paulo`, `USE_TZ=True`.

---

### 🐳 6. Infraestrutura Docker

**`Dockerfile`** — base `python:3.11-slim` (alinhada ao README), instala deps,
define `PYTHONPATH=/app/src` e usa `gunicorn` como `CMD` padrão (produção).

**`docker-compose.yml`** (projeto `findly`) — 5 serviços:

| Serviço | Imagem / build | Função |
| :--- | :--- | :--- |
| `db` | `postgres:15-alpine` | Banco, com *healthcheck* (`pg_isready`) |
| `redis` | `redis:7-alpine` | Cache + broker/result do Celery, com *healthcheck* |
| `web` | build local | Django (`runserver` em dev) + aplica migrações no boot |
| `worker` | build local | Celery worker (tarefas assíncronas) |
| `beat` | build local | Celery beat (tarefas agendadas) |

- **Volumes persistentes:** `postgres_data`, `redis_data`, `media_volume`,
  `static_volume` (os três últimos conforme o README).
- **Rede:** `findly_network` (bridge).
- **Boot ordenado:** `web`/`worker`/`beat` aguardam `db` e `redis` saudáveis;
  somente o `web` roda `migrate` (evita corrida de migrações).
- Os hosts internos (`db`, `redis`) são injetados via `environment`, enquanto o
  restante vem do `.env` (`env_file`).

---

### ✅ 7. Validações executadas

| Verificação | Comando | Resultado |
| :--- | :--- | :--- |
| Django carrega e valida | `python manage.py check` | ✅ `System check identified no issues (0 silenced).` |
| Compose válido | `docker compose config --quiet` | ✅ OK |
| `entrypoint.sh` em LF (compatível com Linux) | inspeção de bytes | ✅ 0 CRLF / 51 LF |
| Makefile com TABs nas receitas | inspeção | ✅ 44 linhas com TAB |

---

### 🚀 8. Como executar

**Opção A — Docker (recomendado):**
```bash
# 1. (primeira vez) copie as variáveis de ambiente
cp .env.example .env
# 2. suba tudo
docker compose up -d --build      # ou: make up
# 3. logs
docker compose logs -f web        # ou: make logs-web
```
> ⚠️ Requer o **Docker Desktop em execução** (o daemon estava parado nesta sessão).

**Opção B — Local (sem Docker):**
```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt   # Windows
# ou: make venv && make install
# suba PostgreSQL e Redis, ajuste o .env e então:
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py runserver
```

**Atalhos (`Makefile`):** rode `make help` para ver todos. Destaques: `make up`,
`make down`, `make logs`, `make migrate`, `make docker-superuser`, `make test`,
`make lint`, `make format`, `make dbshell`, `make reset`.

> 🔧 **Observação sobre o `make` no Windows:** o GNU Make **não está instalado**
> nesta máquina. Alternativas: usar o **Git Bash**, instalar via
> `choco install make` / `scoop install make`, ou usar WSL. Sem isso, use os
> comandos `docker compose ...` diretamente (o Makefile é apenas açúcar sintático).

---

### ⏭️ 9. Pendências e próximos passos (próxima etapa)

1. **⚠️ CRÍTICO — Modelo de usuário customizado:** definir `AUTH_USER_MODEL`
   (ex.: `apps.users.User`) **antes da primeira migração**. Trocar depois exige
   recriar o banco. Deixamos a linha comentada em `settings.py` com um `TODO`.
2. **Criar os apps de domínio** (`python manage.py startapp`), configurando
   `name = "apps.<app>"` nos `AppConfig` e registrando em `LOCAL_APPS`:
   `authentication`, `users`, `items`, `operations`, `audit`.
3. **Máquina de estados do item** (`REPORTADO → EM_CUSTODIA → AGUARDANDO_RETIRADA
   → DEVOLVIDO`, ramo `EXPIRADO/ENCAMINHADO`) com transições auditadas.
4. **Camada de serviços** (`src/services/`): `qrcode_service`, `photo_service`,
   `notification_service` (+ tasks Celery correspondentes).
5. **Endpoints** de auth (login/logout/cadastro/recuperação), users, items e
   operations (custódia, retirada, pontos de coleta), com serializers/viewsets.
6. **Testes** com pytest (`make test`) e configure a geração das primeiras
   migrações.
7. *(Opcional)* Adicionar stack de observabilidade/`nginx` quando formos para
   produção.

---

### 📌 10. Convenções do projeto (a manter)

- **Fat services, skinny views** — views só validam e delegam.
- **`@transaction.atomic`** em toda troca de custódia/entrega.
- **Auditoria inegociável** — toda mudança de status/custódia gera histórico.
- **Lint/format:** `make lint` (ruff) e `make format` (black + ruff --fix).

## 🗓️ 2026-10-14 — Honeypot + proteção do Django Admin

### 🎯 Objetivo
Esconder o Django Admin em um caminho secreto e transformar o clássico `/admin/`
em uma **armadilha (honeypot)** que registra, conta e (opcionalmente) bloqueia
quem tenta acessá-lo — incluindo captura das credenciais digitadas.

### 🧩 Implementação
Novo pacote `src/security/` (infra transversal, registrada em `INSTALLED_APPS`
como `INFRA_APPS` apenas para expor o management command):

| Arquivo | Responsabilidade |
| :--- | :--- |
| `security/honeypot.py` | Views, página-isca, captura de credenciais, contadores e blocklist |
| `security/middleware.py` | `HoneypotBlockMiddleware` — barra IPs bloqueados (403) antes do processamento |
| `security/urls.py` | Rotas das iscas (`/admin` e caminhos extras) |
| `security/management/commands/honeypot_report.py` | Relatório/gerenciamento dos eventos |
| `security/management/commands/gen_secret.py` | Gera `DJANGO_SECRET_KEY` + `DJANGO_ADMIN_URL` |
| `security/tests/test_honeypot.py` | 6 testes (não dependem de Redis) |

### 🔑 Comportamento
- **Admin real** servido em `DJANGO_ADMIN_URL` (padrão `/painel-interno/`).
- **`/admin/` e `/admin/*`** → página de login **falsa** (HTTP 200). `POST`
  registra usuário tentado + tamanho e SHA256 da senha (texto puro opcional).
- **Caminhos isca** (`/wp-admin/`, `/wp-login.php`, `/phpmyadmin/`, `/.env`,
  `admin.php`, `config.php`) → registram e retornam **404**.
- **Captura:** log dedicado `logs/security.log` (rotativo 5MB×5) **+** Redis
  (histórico, contador por IP com TTL, blocklist).
- **Bloqueio:** ao atingir `HONEYPOT_BLOCK_THRESHOLD` (5), o IP entra na
  blocklist e recebe **403**. IPs confiáveis/privados **não** são bloqueados por
  padrão (evita auto-bloqueio em dev).
- **Tarpit** opcional via `HONEYPOT_DELAY_SECONDS`.
- **Degradação segura:** sem Redis, o acesso continua sendo registrado no log e
  a isca é servida normalmente (nada quebra).

### ⚙️ Configurações novas (`.env` / `.env.example` / settings)
`DJANGO_ADMIN_URL`, `HONEYPOT_ENABLED`, `HONEYPOT_DELAY_SECONDS`,
`HONEYPOT_BLOCK_THRESHOLD`, `HONEYPOT_BLOCK_TTL_SECONDS`, `HONEYPOT_MAX_EVENTS`,
`HONEYPOT_LOG_CREDENTIALS`, `HONEYPOT_CAPTURE_PASSWORD_PLAINTEXT`,
`HONEYPOT_TRUSTED_IPS`, `HONEYPOT_BLOCK_PRIVATE_IPS`, `HONEYPOT_EXTRA_PATHS`.

### 🧰 Makefile / Docker
- `make gen-secret` (e `python manage.py gen_secret`) — chaves aleatórias.
- `make report` / `make docker-report` — inspeção dos eventos e blocklist.
- Volume Docker `logs_volume` montado em `/app/logs`.
- `logs/` adicionado ao `.gitignore` e `.dockerignore`.

### ✅ Validações
| Verificação | Resultado |
| :--- | :--- |
| `GET /admin/` | 200 + formulário falso ✅ |
| `POST /admin/` | 200 (captura credenciais) ✅ |
| `/painel-interno/` (admin real) | 302 (login) ✅ |
| `/wp-admin/`, `/.env` | 404 ✅ |
| `pytest src/security/tests` | 6 passed ✅ |

> 🔎 **Nota:** `docker compose config` OK. O bloqueio via Redis só é exercido de
> fato com o Redis no ar.

---

## 🗓️ 2026-10-14 — App `users` + modelo de usuário customizado

### 🎯 Objetivo
Criar o app `users` e travar `AUTH_USER_MODEL` **antes da primeira migração**
(login por e-mail + papéis), conforme a pendência crítica levantada no bootstrap.

### 🧩 Implementação
App criado em `src/apps/users/` (nome do `AppConfig` = `apps.users`):

| Arquivo | Responsabilidade |
| :--- | :--- |
| `models.py` | `User` (AbstractBaseUser + PermissionsMixin) e `Role` (TextChoices) |
| `managers.py` | `UserManager` com `create_user`/`create_superuser` (por e-mail) |
| `forms.py` | `UserCreationForm`/`UserChangeForm` (admin adaptado p/ e-mail) |
| `admin.py` | `UserAdmin` customizado, registrado no admin secreto |
| `migrations/0001_initial.py` | Migração inicial do modelo |
| `tests/test_models.py` | 5 testes do modelo/manager |

### 🔑 Modelo `User`
- Login por **e-mail** (`USERNAME_FIELD = "email"`), sem `username`.
- `Role`: `common` (Usuário Comum), `operator` (Operador de Ponto de Coleta),
  `admin` (Administrador).
- Campos: `email` (único), `full_name`, `phone`, `role`, `is_active`, `is_staff`,
  `date_joined`; propriedades `short_name`, `is_operator`, `is_admin`.
- `AUTH_USER_MODEL = "users.User"` ativado em `settings.py`; `"apps.users"`
  adicionado a `LOCAL_APPS`.

### 🛠️ Ajuste de configuração
- `connect_timeout` (default 5s) adicionado às `OPTIONS` do PostgreSQL para evitar
  que comandos fiquem pendurados quando o banco está indisponível.

### ✅ Validações
| Verificação | Resultado |
| :--- | :--- |
| `manage.py check` | 0 issues ✅ |
| `makemigrations users` | `0001_initial` gerado ✅ |
| `migrate` (SQLite temporário) | todas as migrações aplicadas ✅ |
| `create_user` / `create_superuser` | papéis, hashing e flags corretos ✅ |
| `pytest src/apps/users/tests` | 5 passed ✅ |

> ℹ️ As migrações foram geradas/validadas usando **SQLite temporário**
> (`DATABASE_URL=sqlite:///db.sqlite3`), pois o Postgres/Docker não estava
> disponível. As migrações são agnósticas de banco; o `db.sqlite3` foi removido.
> No ambiente real, rode `make docker-migrate` (ou `manage.py migrate`) com o
> Postgres no ar.

### ⏭️ Próximos passos
1. `authentication`: cadastro, login/logout (JWT) e recuperação de senha.
2. Serializers + ViewSet de `users` (perfil, `/me`, listagem admin).
3. Permissões por papel (common/operator/admin) e depois `items`.

## 🗓️ 2026-10-14 — Teste end-to-end do `/admin` + honeypot (bug de CSRF)

### 🎯 Objetivo
Validar em **HTTP real** (não só test client) o admin oculto e o honeypot.

### 🧪 Procedimento
Como o Postgres/Docker não estava disponível, o teste rodou com **SQLite
temporário** (`DATABASE_URL=sqlite:///db.sqlite3`): `migrate` →
`createsuperuser --email` → `runserver`. O `db.sqlite3` foi removido ao final.

### 📊 Resultados
| Requisição | Resposta | OK? |
| :--- | :--- | :--- |
| `GET /admin/` | 200 (formulário-isca) | ✅ |
| `POST /admin/` (com credenciais) | 200 + captura no log | ✅ |
| `POST /admin/login/` | 200 + captura no log | ✅ |
| `GET /painel-interno/` | 302 → login do admin | ✅ |
| Login real (`POST /painel-interno/login/`) | 302 → `GET /painel-interno/` 200 (admin) | ✅ |
| `GET /wp-admin/`, `GET /.env` | 404 | ✅ |

### 🐞 Bug encontrado e corrigido
- **Sintoma:** `POST /admin/` retornava **403** em produção.
- **Causa:** o `CsrfViewMiddleware` bloqueava o POST (o formulário-isca não tem
  token CSRF) — ou seja, **as credenciais nunca chegavam à view** e nada era
  capturado. Log: `Forbidden (CSRF cookie not set.): /admin/`.
- **Correção:** view do honeypot marcada com `@csrf_exempt` (a isca precisa
  aceitar o POST para capturar). Além disso, o **username tentado** passou a
  constar na linha de log (visível mesmo sem Redis).
- **Teste de regressão:** `test_post_sem_csrf_token_e_aceito` usando
  `Client(enforce_csrf_checks=True)` — o test client padrão **não** valida CSRF,
  por isso o bug não havia sido detectado antes.

### ✅ Validações
- `pytest src/security/tests/test_honeypot.py` → **7 passed**.
- Captura confirmada no `logs/security.log`:
  `Honeypot [admin_login_attempt] ... username='admin'`.

> ℹ️ **Observação:** o `runserver` exige banco no boot (`check_migrations()`),
> então sem Postgres ele não sobe. Em produção/dev use o Docker
> (`make up`) ou tenha o Postgres no ar.

---

## 🗓️ 2026-10-14 — Subida dos containers + correções de Docker e Makefile

### 🎯 Objetivo
Colocar a stack completa no ar (`docker compose up`) para demonstração e
corrigir os problemas que impediam `web`, `worker` e `beat` de subir.

### 🐞 Problemas encontrados e corrigidos

**1. `web`/`worker`/`beat` caiam com `ModuleNotFoundError: django_extensions`**
- **Causa:** com `DJANGO_DEBUG=True`, o `settings.py` adiciona `django_extensions`
  ao `INSTALLED_APPS`, mas a imagem Docker instalava apenas `requirements.txt`
  (base), não o `requirements-dev.txt`.
- **Correção (Dockerfile):** build arg `INSTALL_DEV` (default `true`) que instala
  também o `requirements-dev.txt`. Em produção:
  `docker build --build-arg INSTALL_DEV=false .`

**2. `beat` caía por subir antes das migrações**
- **Causa:** `django_celery_beat` precisa do schema criado pelas migrações; o
  `depends_on` esperava apenas o `db` ficar *healthy*, não as migrações.
- **Correção (docker-compose.yml):** novo serviço **one-shot `migrate`**
  (`python manage.py migrate --noinput`). `web`, `worker` e `beat` agora usam
  `depends_on: migrate: condition: service_completed_successfully` e rodam com
  `RUN_MIGRATIONS=0` (as migrações são aplicadas uma única vez pelo `migrate`).

**3. Evento do honeypot sem o contador `hits`**
- **Causa:** em `honeypot.py`, o evento era gravado no Redis **antes** de
  `_register_hit()` calcular o `hits`.
- **Correção:** recalcular o `hits` antes de `_store_event()`; o log agora também
  inclui `hits=N`. Confirmado: `admin_login_attempt ... hits=4`.

**4. `make help` / `make clean` quebrados no Windows**
- **Causa:** o GNU Make no Windows usa o **cmd.exe**; `help` dependia de
  `grep/awk/sort` e `clean` de `find/rm -rf` (indisponíveis), além de mojibake
  nos acentos.
- **Correções (Makefile):**
  - `help` reescrito em **make puro** (`define HELP_TEXT` + `$(info)`), sem shell.
  - `clean` reescrito em **Python** (portável), ignorando `.venv`.
  - No-op portátil `$(NOOP)` (`@rem` no Windows / `@:` no Unix) para evitar o
    `Nothing to be done for 'help'`.
  - Texto do help em ASCII (evita mojibake no cmd).

**5. `MANAGE` expandia sem o interpretador do venv**
- **Causa:** `MANAGE := $(VENV_PY) manage.py` (expansão imediata) aparecia
  **antes** da definição de `VENV_PY` no `ifeq ($(OS))` → `$(VENV_PY)` vazio,
  resultando em só `manage.py`.
- **Correção:** mover `MANAGE :=` para **depois** do bloco `ifeq`.
  (Só foi descoberto agora porque o `make` passou a estar instalado.)

### 🐳 Stack no ar
`db` e `redis` (healthy), `migrate` (Exited 0), `web :8000`, `worker` e `beat` (up).

| Endpoint | Resultado |
| :--- | :--- |
| `GET /admin/` (isca) | 200 ✅ |
| `POST /admin/` (captura) | 200 ✅ |
| `GET /painel-interno/` (admin real) | 200 ✅ |
| `GET /api/docs/` (Swagger) | 200 ✅ |
| `GET /wp-admin/` | 404 ✅ |
| `make check` | 0 issues ✅ |
| `make help` / `make clean` / `make gen-secret` | OK ✅ |

### 🔧 Comandos úteis da demo
- Superusuário: `admin@findly.local` / `admin12345` (criado via
  `docker compose exec web python manage.py createsuperuser --noinput --email ...`).
- Captura: `make docker-report` (eventos + blocklist no Redis).
- Logs: `docker compose logs -f web`.

> ℹ️ O IP capturado é o **gateway do Docker** (`172.x`), pois a requisição chega
> pela rede interna. Bloqueio de IPs privados fica desligado por padrão
> (`HONEYPOT_BLOCK_PRIVATE_IPS=False`).

---

## 🗓️ 2026-10-28 — App `authentication` (JWT: cadastro, login, logout, verificação e reset)

### 🎯 Objetivo
Implementar o módulo **Autenticação** do README: cadastro com verificação de
conta, login/logout com JWT (par `access`/`refresh`) e recuperação de senha via
token temporário de curta duração.

### 📁 Estrutura criada
| Arquivo | Responsabilidade |
| :--- | :--- |
| `apps/authentication/tokens.py` | Tokens de uso único (e-mail e reset) com `key_salt` distintos e expiração configurável |
| `apps/authentication/emails.py` | Renderização e envio dos e-mails (link do front-end + `uid`/`token`) |
| `apps/authentication/serializers.py` | Cadastro, login, logout, verificação e reset |
| `apps/authentication/services.py` | `blacklist_user_tokens()` (revoga sessões após reset) |
| `apps/authentication/views.py` | Views com throttling escopado e documentação OpenAPI |
| `apps/authentication/templates/...` | E-mails em texto (`verify_email.txt`, `password_reset.txt`) |
| `apps/users/serializers.py` | `UserSerializer` (leitura), reutilizado na resposta do login |
| `apps/authentication/tests/` | 38 testes (cadastro, login, refresh/logout, verificação, reset, tokens) |

### 🔌 Rotas (`/api/auth/`)
| Método | Rota | Descrição |
| :--- | :--- | :--- |
| POST | `register/` | Cria a conta (nasce inativa) e envia confirmação |
| POST | `login/` | E-mail + senha → `access`, `refresh`, `user` |
| POST | `refresh/` | Rotaciona o par e invalida o refresh anterior |
| POST | `logout/` | Blacklist do refresh (exige autenticação) |
| POST | `verify-email/` | Ativa a conta com `uid` + `token` |
| POST | `resend-verification/` | Reenvia confirmação (resposta genérica) |
| POST | `password-reset/` | Solicita link temporário (resposta genérica) |
| POST | `password-reset/confirm/` | Define a nova senha e revoga sessões |

### 🔐 Decisões de segurança
- **Contas nascem inativas** (`AUTH_REQUIRE_EMAIL_VERIFICATION=True`): o login só
  funciona após `verify-email/`. Em dev o e-mail sai no console do container.
- **Tokens independentes por fluxo**: `key_salt` diferente em
  `EmailVerificationTokenGenerator` e `FindlyPasswordResetTokenGenerator` — um
  token de verificação **não** serve para resetar senha (e vice-versa).
- **Uso único**: o token de verificação inclui `is_active` no hash (invalida após
  a ativação); o de reset inclui `password`/`last_login` (invalida após o uso).
- **Expiração curta**: `PASSWORD_RESET_TIMEOUT=3600` e
  `EMAIL_VERIFICATION_TIMEOUT=86400` (segundos), configuráveis no `.env`.
- **Anti-enumeração**: `password-reset/` e `resend-verification/` sempre
  respondem `202` com mensagem genérica.
- **Throttling escopado**: `auth` (20/min), `register` (5/h) e
  `password_reset` (5/h) — configurável por env.
- **Revogação de sessões**: ao redefinir a senha, todos os `OutstandingToken` do
  usuário vão para a blacklist; refreshes antigos passam a falhar.
- **Logout restrito ao dono**: um usuário autenticado não consegue revogar o
  refresh de outra conta (comparação de `user_id`).

### ✅ Validações
| Verificação | Resultado |
| :--- | :--- |
| `manage.py check` | 0 issues ✅ |
| `makemigrations --check` | No changes detected ✅ |
| `pytest src/apps/authentication` | **38 passed** ✅ |
| `pytest src/apps/users` | 5 passed ✅ |
| `ruff check` / `black --check` | limpos ✅ |
| `manage.py spectacular` | 8 rotas, sem warnings ✅ |

> ℹ️ Os testes usam **SQLite temporário** e cache em memória (`LocMemCache`),
> sem depender de Postgres/Redis. O throttle é neutralizado nos testes.

### ⏭️ Próximos passos
1. Serializers + ViewSet de `users` (perfil, `/me`, listagem/gestão por papel).
2. Permissões por papel (`common`/`operator`/`admin`).
3. Depois: `items` (achados/perdidos + máquina de estados), `operations`, `audit`.

## 🗓️ 2026-10-28 — App `users` (perfil, `/me` e gestão de contas por papel)

### 🎯 Objetivo
Expor o módulo **Usuários** do README: perfil/dados cadastrais, informações de
contato e controle de permissões (Usuário Comum, Operador de Ponto de Coleta e
Administrador).

### 📁 Estrutura criada/alterada
| Arquivo | Responsabilidade |
| :--- | :--- |
| `apps/users/permissions.py` | `IsAdminRole` (papel `admin`/superusuário) e `IsOperatorOrAdmin` (reutilizável em itens/operações) |
| `apps/users/serializers.py` | `UserSerializer` (leitura), `MeSerializer` (perfil) e `AdminUserUpdateSerializer` (gestão) |
| `apps/users/views.py` | `MeView` (perfil) e `UserViewSet` (listagem/detalhe/edição) |
| `apps/users/urls.py` | Rotas em `/api/users/` |
| `apps/users/forms.py` | `UserChangeForm` com `fields` explícitos (corrige `DJ007` do ruff) |
| `apps/users/tests/test_api.py` + `conftest.py` | 19 testes de API (perfil, permissões, gestão e revogação) |

### 🔌 Rotas (`/api/users/`)
| Método | Rota | Quem acessa | Descrição |
| :--- | :--- | :--- | :--- |
| GET | `me/` | autenticado | Perfil do próprio usuário |
| PUT/PATCH | `me/` | autenticado | Atualiza `full_name` e `phone` |
| GET | `/` | admin | Lista paginada (filtro `role`/`is_active`, busca e ordenação) |
| GET | `{id}/` | admin | Detalhe de uma conta |
| PUT/PATCH | `{id}/` | admin | Corrige dados, muda papel e (des)ativa a conta |

### 🔐 Decisões
- **E-mail e papel são somente leitura no perfil**: o e-mail é o identificador de
  login (trocá-lo exigiria novo ciclo de verificação) e o papel é controlado pela
  administração. No `me/`, só `full_name` e `phone` são editáveis.
- **Sem criação/exclusão pela API de gestão**: contas nascem pelo cadastro
  público e são **desativadas** (`is_active=False`), preservando histórico e
  auditoria. Métodos `POST`/`DELETE` respondem `405`.
- **Admin não edita o próprio registro** (`400`): evita rebaixar ou desativar a
  si mesmo por engano; os próprios dados ficam em `/api/users/me/`.
- **Superusuário não perde o papel `admin`**, mesmo quando editado por outro
  administrador.
- **Desativação revoga sessões**: os *refresh tokens* vão para a blacklist e o
  *access token* deixa de autenticar (o `JWTAuthentication` exige `is_active`).
- **`IsOperatorOrAdmin`** já fica pronto para os próximos apps (itens/operações).

### ✅ Validações
| Verificação | Resultado |
| :--- | :--- |
| `manage.py check` | 0 issues ✅ |
| `makemigrations --check` | No changes detected ✅ |
| `pytest src/apps/users` | **24 passed** (5 modelo + 19 API) ✅ |
| `pytest src/apps/authentication` | 38 passed ✅ |
| `ruff check` / `black --check` | limpos ✅ |
| `manage.py spectacular` | 3 rotas de usuários, sem warnings ✅ |

### ⏭️ Próximos passos
1. App `items` (achados/perdidos + máquina de estados e histórico vinculado).
2. App `operations` (custódia, pontos de coleta, claims/retiradas + QR Code).
3. App `audit` (trilha de auditoria) e serviços transversais (fotos/notificações).

## 🗓️ 2026-10-28 — Collection Postman (autenticação + usuários) e environment

### 🎯 Objetivo
Criar artefatos prontos para apresentar a autenticação e documentar, para o time
de front-end, todos os endpoints disponíveis (auth + usuários), com tokens
gerenciados automaticamente pelas requisições.

### 📁 Estrutura criada
| Arquivo | Conteúdo |
| :--- | :--- |
| `postman/collections/Findly API/` | Collection v3 com 13 requisições em 2 pastas |
| `postman/environments/Findly Local.environment.yaml` | `base_url`, credenciais demo e variáveis de token/verificação/reset |
| `README.md` | Seção 7 com instruções de importação e uso |

### 🔌 Requisições
- **1. Autenticação:** Cadastro, Verificar e-mail, Login, Renovar token, Logout,
  Reenviar verificação, Solicitar reset e Confirmar reset.
- **2. Usuários:** Meu perfil, Atualizar perfil, Listar (admin), Detalhar (admin)
  e Editar (admin).

### ⚙️ Automação dos scripts
- Login salva `access_token`, `refresh_token` e `user_id` no environment.
- Refresh rotaciona e atualiza o par automaticamente.
- Logout e reset limpam os tokens; reset também troca `login_password`.
- Cada requisição tem `pm.test` (status e formato) para servir de exemplo ao front.

### ✅ Validações
| Verificação | Resultado |
| :--- | :--- |
| `postman collection lint` | 0 errors / 0 warnings ✅ |
| `postman environment lint` | 0 errors / 0 warnings ✅ |
| `postman workspace lint` | 16 recursos, sem issues ✅ |
| Login → perfil → refresh → listagem admin → logout | 6 requests, 12 assertions, 0 falhas ✅ |
| Cadastro → verificação → login | `201`/`200`/`200` ✅ |
| Solicitar reset → confirmar → login com nova senha | `202`/`200`/`200` ✅ |

> A execução foi feita contra um Django local (SQLite + cache em memória), com
> e-mail no console — o mesmo comportamento do `docker compose` em dev.

## 🗓️ 2026-11-09 — App `items`: achados, perdidos, máquina de estados e fotos

### 🎯 Objetivo
Implementar o primeiro app de domínio do núcleo do Findly: cadastro de objetos
encontrados e alertas de perdidos, com ciclo de vida controlado, permissões por
papel, filtros e upload seguro de fotos.

### 📁 Estrutura criada
| Arquivo | Conteúdo |
| :--- | :--- |
| `src/apps/items/models.py` | `FoundItem`, `LostReport`, `ItemPhoto` + enums de categoria/status |
| `src/apps/items/services.py` | Máquina de estados transacional (`transition_found_item`) |
| `src/apps/items/permissions.py` | Autor/operador/admin, fotos e alertas |
| `src/apps/items/serializers.py` | Leitura/escrita separadas, status e upload |
| `src/apps/items/views.py` + `urls.py` | 12 rotas em `/api/items/` |
| `src/apps/items/filters.py` | Status, categoria, período, `mine` e busca |
| `src/apps/items/admin.py` | Registro no admin secreto + inline de fotos |
| `src/services/photo_service.py` | Validação, orientação, resize, JPEG e remoção de EXIF |
| `src/apps/items/migrations/0001_initial.py` | Migração inicial |
| `src/apps/items/tests/` | 51 testes |

### 🔌 Endpoints
- **Achados:** `GET/POST /api/items/found/`, `GET/PATCH /api/items/found/{code}/`,
  `POST .../status/`, `POST .../photos/`, `DELETE .../photos/{id}/`.
- **Perdidos:** `GET/POST /api/items/lost/`, `GET/PATCH /api/items/lost/{code}/`,
  `POST .../cancel/`.
- Código público de 10 caracteres em vez de ID sequencial; filtros de status,
  categoria, período, `mine` e busca textual; paginação global (20/página).

### 🔁 Máquina de estados
`REPORTADO → EM_CUSTODIA → AGUARDANDO_RETIRADA → DEVOLVIDO`, com saída para
`EXPIRADO`/`ENCAMINHADO`. Estados finais são terminais; saltos inválidos e status
repetido retornam `400`. Toda transição passa por serviço atômico — a view nunca
grava `status` diretamente.

### 🔐 Permissões e privacidade
- Autor edita o achado apenas em `REPORTADO`; depois, só operador/admin.
- Status e custódia: somente operador/admin.
- Alertas de perda: dono enquanto `ABERTO`; admin sempre.
- `reported_by`/`owner` expõem somente `id` e `full_name` (sem e-mail/telefone).
- Sem `DELETE` de itens: o ciclo termina em estado final (histórico preservado).

### 🖼️ Serviço de fotos
- Extensões `jpg/jpeg/png/webp`, máximo 5 MB.
- `ImageOps.exif_transpose` antes de descartar metadados.
- Maior lado limitado a 1600 px, recompressão JPEG (q=85).
- Transparência achatada em fundo branco; nomes aleatórios em
  `media/items/<public_code>/`.
- Remoção da foto apaga o arquivo e o registro.

### ✅ Validações
| Verificação | Resultado |
| :--- | :--- |
| `pytest src/apps/items` | **51 passed** ✅ |
| `pytest` (suíte completa) | **120 passed** ✅ |
| `manage.py check` | sem issues ✅ |
| `makemigrations --check --dry-run` | sem drift ✅ |
| `spectacular --validate` | 0 erros / 0 warnings (após `ENUM_NAME_OVERRIDES`) ✅ |
| `ruff` + `black` (arquivos novos) | limpos ✅ |

### 📌 Decisões desta etapa
- Fotos em disco local (`MEDIA_ROOT`/volume Docker) — troca para S3 fica isolada
  no serviço de fotos.
- Listagem exige autenticação; contato do autor não é exposto.
- Categorias fixas em código (`TextChoices`) para evitar tabela de apoio nesta fase.
- QR de retirada (24 h, uso único) será implementado no app `operations`.

### ⏭️ Próximos passos
1. App `audit`: trilha imutável e integração em `transition_found_item`.
2. App `operations`: custódia, pontos de coleta, claims e retirada via QR.
3. Serviços restantes (QR, notificações) e coleção Postman de itens.

## 🗓️ 2026-11-09 — App `audit`: trilha imutável e histórico de itens

### 🎯 Objetivo
Garantir rastreabilidade inegociável: toda criação de item e toda mudança de
status passa a gravar um evento no mesmo bloco transacional da operação.

### 📁 Estrutura criada
| Arquivo | Conteúdo |
| :--- | :--- |
| `src/apps/audit/models.py` | `AuditEvent` imutável + `AuditAction` |
| `src/apps/audit/services.py` | `record_event` (usado por items) |
| `src/apps/audit/permissions.py` | Histórico: autor, operador ou admin |
| `src/apps/audit/serializers.py` | Eventos somente leitura |
| `src/apps/audit/filters.py` | Item, ação, período e busca |
| `src/apps/audit/views.py` + `urls.py` | Histórico aninhado + consulta admin |
| `src/apps/audit/admin.py` | Admin somente leitura |
| `src/apps/audit/migrations/0001_initial.py` | Migração inicial |
| `src/apps/audit/tests/` | 25 testes |

### 🔌 Endpoints
- `GET /api/items/found/{code}/history/` — autor, operador ou admin (sem
  paginação; ordem do mais recente para o mais antigo).
- `GET /api/audit/` e `GET /api/audit/{id}/` — apenas admin, com filtros por
  `item`, `action`, `date_from`, `date_to`, busca e ordenação.
- `POST/PATCH/DELETE` nesses recursos retornam `405`.

### 🔒 Imutabilidade e atomicidade
- `AuditEvent.save()` em registro existente e `delete()` levantam `ValueError`.
- Admin sem permissão de criação, edição ou exclusão.
- `AuditAction`: `CREATED` e `STATUS_CHANGED` em uso; `CUSTODY_TRANSFERRED`,
  `CLAIM_APPROVED`, `CLAIM_REJECTED` e `WITHDRAWAL_CONFIRMED` reservadas para
  `operations`.
- `transition_found_item` grava `STATUS_CHANGED` antes de retornar; o
  `perform_create` de itens grava `CREATED` sob `@transaction.atomic`.
- Falha simulada na auditoria reverte a transição e o cadastro (testado).

### ✅ Validações
| Verificação | Resultado |
| :--- | :--- |
| `pytest src/apps/audit` | **25 passed** ✅ |
| `pytest` (suíte completa) | **145 passed** ✅ |
| `manage.py check` | sem issues ✅ |
| `makemigrations --check --dry-run` | sem drift ✅ |
| `spectacular --validate` | 0 erros / 0 warnings ✅ |
| `ruff` + `black` (arquivos novos) | limpos ✅ |

### 📌 Decisões desta etapa
- `responsible` anulável para permitir ações automáticas futuras.
- FK de ponto de coleta adiada para `operations` (evita dependência circular).
- Histórico do item sem paginação (volume pequeno por item).
- Import local de `apps.audit` em `items` mantém a dependência em uma direção.

### ⏭️ Próximos passos
1. App `operations`: pontos de coleta, custódia, claims e retirada via QR.
2. Serviços de QR (24 h, uso único) e notificações.
3. Coleção Postman de itens/auditoria.

## 🗓️ 2026-11-09 — App `operations`: pontos, custódia, claims e retirada via QR

### 🎯 Objetivo
Fechar o ciclo operacional do item: receber em um ponto de coleta, registrar
quem detém a posse física, avaliar reivindicações e liberar a retirada com QR
Code temporário e de uso único — tudo auditado na mesma transação.

### 📁 Estrutura criada
| Arquivo | Conteúdo |
| :--- | :--- |
| `src/apps/operations/models.py` | `CollectionPoint`, `CustodyRecord`, `Claim`, `WithdrawalAuthority` |
| `src/apps/operations/services.py` | Custódia, claims e retirada (transacionais) |
| `src/apps/operations/permissions.py` | Custódia e claims por autor/operador/admin |
| `src/apps/operations/serializers.py` | Pontos, custódia, claims e QR |
| `src/apps/operations/filters.py` | Pontos e claims (status, item, período, `mine`) |
| `src/apps/operations/views.py` + `urls.py` | Rotas em `/api/operations/` |
| `src/apps/operations/admin.py` | Admin somente leitura para custódia/claims/QR |
| `src/services/qrcode_service.py` | Etiqueta e QR de retirada (PNG) |
| `src/apps/operations/migrations/0001_initial.py` | Migração inicial |
| `src/apps/audit/migrations/0002_*.py` | FK `collection_point` + `CLAIM_CANCELLED` |
| `src/apps/operations/tests/` | 78 testes |

### 🔌 Endpoints
- **Pontos:** `GET/POST /api/operations/points/`, `GET/PATCH .../{id}/` (escrita
  apenas admin; sem DELETE).
- **Custódia:** `GET .../items/found/{code}/custody/`,
  `POST .../custody/transfer/`, `GET .../label/` (etiqueta QR PNG).
- **Claims:** `GET/POST .../items/found/{code}/claims/`,
  `GET /api/operations/claims/`, `.../{id}/`, e ações `approve`, `reject`,
  `cancel`.
- **Retirada:** `POST /api/operations/withdrawals/confirm/`.

### 🔁 Regras de negócio
- Cadastro do achado abre custódia inicial com quem registrou (sem evento extra;
  o `CREATED` já cobre a criação).
- Transferência para ponto fecha o registro anterior, valida capacidade e
  vínculo operador→ponto, muda `REPORTADO → EM_CUSTODIA` e grava
  `CUSTODY_TRANSFERRED`.
- Quem cadastrou o achado não pode reivindicá-lo; não há claim pendente duplicado
  por usuário/item; item terminal não aceita claim.
- Aprovação exige item em `EM_CUSTODIA`/`AGUARDANDO_RETIRADA`, move para
  `AGUARDANDO_RETIRADA`, emite QR de 24 h e recusa os demais pendentes.
- Retirada valida token (aceita payload do QR), expiração e uso único; move para
  `DEVOLVIDO`, fecha a custódia e grava `WITHDRAWAL_CONFIRMED`.
- `AuditEvent` ganhou FK opcional `collection_point` e a ação `CLAIM_CANCELLED`.

### ✅ Validações
| Verificação | Resultado |
| :--- | :--- |
| `pytest src/apps/operations` | **78 passed** ✅ |
| `pytest` (suíte completa) | **223 passed** ✅ |
| `manage.py check` | sem issues ✅ |
| `makemigrations --check --dry-run` | sem drift ✅ |
| `spectacular --validate` | 0 erros / 0 warnings ✅ |
| `ruff` + `black` (arquivos novos) | limpos ✅ |

### 📌 Decisões desta etapa
- Claims só podem ser aprovados com o item sob custódia de ponto (retirada
  presencial).
- Operador só transfere para ponto do qual é responsável (quando o ponto tem
  operadores cadastrados).
- QR de retirada é persistido em `media/qrcodes/withdrawals/<token>.png`; a
  etiqueta do item é gerada sob demanda.
- Cancelamento de claim gera evento próprio (`CLAIM_CANCELLED`).

### ⏭️ Próximos passos
1. Serviço de notificações (match, custódia e retirada).
2. Tarefas agendadas: expiração de itens e limpeza de QR vencido.
3. Coleção Postman de itens, operações e auditoria.

## 🗓️ 2026-11-09 — Serviço de notificações (match, custódia e retirada)

### 🎯 Objetivo
Avisar por e-mail/push os envolvidos no ciclo do item: donos de alertas de perda
quando surge um achado compatível, autor do achado nas trocas de custódia,
reivindicante na liberação da retirada e ambos na entrega final.

### 📁 Estrutura criada
| Arquivo | Conteúdo |
| :--- | :--- |
| `src/services/notification_service.py` | Matching, mensagens, canais e agendamento pós-commit |
| `src/apps/items/templates/items/notifications/` | `match.txt`, `lost_report_matches.txt` |
| `src/apps/operations/templates/operations/notifications/` | `custody.txt`, `awaiting_pickup.txt`, `withdrawal_confirmed.txt` |
| `src/apps/items/tests/test_notifications.py` | 12 testes (match, janela, falha de SMTP) |
| `src/apps/operations/tests/test_notifications.py` | 4 testes (custódia, aprovação, retirada) |

### 🔁 Regras implementadas
- **Match** exige mesma categoria, achado posterior à perda (janela de 30 dias)
  e ao menos uma palavra significativa em comum (sem acentos/stopwords, 4+ letras).
- Notificações nos dois sentidos: ao cadastrar o achado e ao abrir o alerta.
- Alertas cancelados, achados terminais e itens encontrados antes da perda são
  ignorados; até 5 notificações por evento (`MATCH_NOTIFICATION_LIMIT`).
- Transferência avisa o autor do achado; aprovação avisa o reivindicante;
  retirada avisa reivindicante + autor.
- Envio agendado com `transaction.on_commit`; rollback não dispara mensagem.
- Falhas de SMTP/push são logadas e não quebram a operação.
- Canal de push opcional (`NOTIFICATIONS_PUSH_ENABLED`); sem provedor, loga.

### ✅ Validações
| Verificação | Resultado |
| :--- | :--- |
| `pytest src/apps/items/tests/test_notifications.py src/apps/operations/tests/test_notifications.py` | **16 passed** ✅ |
| `pytest` (suíte completa) | **238 passed** ✅ |
| `manage.py check` | sem issues ✅ |
| `makemigrations --check --dry-run` | sem drift ✅ |
| `spectacular --validate` | 0 erros / 0 warnings ✅ |
| `ruff` + `black` (arquivos alterados) | limpos ✅ |

### 📌 Decisões desta etapa
- Notificação é efeito colateral: nunca participa da transação de negócio.
- O token do QR **não** vai no e-mail; a mensagem aponta para a conta autenticada.
- Push fica atrás de flag até a integração com um provedor (FCM/APNs/Web Push).

### ⏭️ Próximos passos
1. Tarefas agendadas: expiração de itens e limpeza de QR vencido.
2. Coleção Postman de itens, operações e auditoria.
3. Revisar envio de notificações via Celery quando o broker estiver disponível.

## 🗓️ 2026-11-09 — Manutenção automática (tarefas agendadas)

### 🎯 Objetivo
Fechar o ciclo de vida dos itens sem intervenção manual: encerrar achados e
alertas de perda antigos e limpar os PNGs de QR de retirada já vencidos,
preservando a trilha de auditoria.

### 📁 Estrutura criada
| Arquivo | Conteúdo |
| :--- | :--- |
| `src/apps/items/tasks.py` | `expire_found_items` e `expire_lost_reports` |
| `src/apps/operations/tasks.py` | `cleanup_expired_withdrawal_qrs` |
| `src/apps/items/management/commands/setup_periodic_tasks.py` | Registro idempotente no `django_celery_beat` |
| `src/apps/items/tests/test_tasks.py` | 8 testes (expiração e agendamento) |
| `src/apps/operations/tests/test_tasks.py` | 5 testes (limpeza de QR) |

### 🔁 Regras implementadas
- **Expiração de achado:** usa `updated_at`; qualquer transferência, mudança de
  status ou decisão renova o prazo (`ITEM_EXPIRATION_DAYS`, padrão 90 dias).
- A transição para `EXPIRADO` grava `STATUS_CHANGED` com responsável nulo e
  recusa os claims pendentes na **mesma transação** (`CLAIM_REJECTED`, também
  sem responsável), via `reject_claim(user=None)`.
- **Expiração de alerta:** `LostReport` aberto com `lost_at` além de
  `LOST_REPORT_EXPIRATION_DAYS` vira `EXPIRADO`.
- **Limpeza de QR:** apaga só o PNG expirado há mais de
  `WITHDRAWAL_QR_RETENTION_DAYS` e limpa `qr_image`; o `WithdrawalAuthority`
  permanece para histórico/auditoria.
- Estados terminais (`DEVOLVIDO`, `EXPIRADO`, `ENCAMINHADO`) e alertas já
  cancelados/expirados não são tocados.
- `setup_periodic_tasks` é idempotente e roda no serviço `migrate` do Docker
  Compose, logo após `migrate`.
- Agendamentos (fuso `America/Sao_Paulo`): itens às 03:00, alertas às 03:15 e
  limpeza de QR às 03:30.

### ✅ Validações
| Verificação | Resultado |
| :--- | :--- |
| `pytest src/apps/items/tests/test_tasks.py src/apps/operations/tests/test_tasks.py` | **13 passed** ✅ |
| `pytest` (suíte completa) | **251 passed** ✅ |
| `manage.py check` | sem issues ✅ |
| `makemigrations --check --dry-run` | sem drift ✅ |
| `spectacular --validate` | 0 erros / 0 warnings ✅ |
| `ruff` + `black` (arquivos alterados) | limpos ✅ |

### 📌 Decisões desta etapa
- Expiração é ação do sistema: auditoria com `responsible=None`.
- QR expirado não apaga o registro de autorização — só o arquivo, mantendo a
  rastreabilidade da emissão.
- Tarefas toleram execução concorrente com `select_for_update` por item.
- `reject_claim` passou a aceitar `user=None` (recusa automática).

### ⏭️ Próximos passos
1. Coleção Postman de itens, operações e auditoria.
2. Revisar envio de notificações via Celery quando o broker estiver disponível.

## 🗓️ 2026-11-09 — Coleção Postman de itens, operações, auditoria e manutenção

### 🎯 Objetivo
Fechar a collection Postman para o front consumir toda a API: autenticação e
usuários já existiam; faltavam itens, operações, auditoria e manutenção.

### 📁 Estrutura criada
| Pasta | Requisições | Conteúdo |
| :--- | :--- | :--- |
| `3 - Itens` | 12 | Achados, perdidos, fotos e máquina de estados |
| `4 - Operacoes` | 14 | Pontos, custódia, claims e retirada por QR |
| `5 - Auditoria` | 3 | Histórico do item e trilha global (admin) |
| `6 - Manutencao` | 4 | Verificação das tarefas automáticas |

Total da collection: **46 requisições** em 6 pastas, com `definition.yaml` por
pasta e descrição do fluxo completo na definição da collection. O environment
`Findly Local` ganhou as variáveis encadeadas `found_code`, `lost_code`,
`photo_id`, `point_id`, `point_name`, `point_address`, `point_capacity`,
`claim_id`, `claim_message`, `withdrawal_token` e `audit_event_id`.

### 🔁 Encadeamento dos scripts
- Cadastrar/listar achado grava `found_code`; perdido grava `lost_code`;
  upload grava `photo_id`.
- Criar/listar ponto grava `point_id`; abrir/listar claim grava `claim_id`.
- Aprovar claim grava `withdrawal_token`; confirmar retirada limpa o token.
- A pasta 6 apenas **verifica** estados (`EXPIRADO`, claims recusadas,
  `STATUS_CHANGED` com `responsible = null`), porque notificações e manutenção
  não têm rota HTTP.

### ✅ Validações
| Verificação | Resultado |
| :--- | :--- |
| `postman collection lint "postman/collections/Findly API"` | **46 scanned, 0 errors, 0 warnings** ✅ |
| `postman environment lint "postman/environments/Findly Local.environment.yaml"` | limpo ✅ |
| Fluxo HTTP real com `config.smoke_settings` (SQLite + LocMem) | login → achado → ponto → custódia → claim → aprovação → retirada **OK** ✅ |
| Histórico do item após o fluxo | 7 eventos: `CREATED`, `CUSTODY_TRANSFERRED`, `CLAIM_APPROVED`, `WITHDRAWAL_CONFIRMED` + `STATUS_CHANGED` ✅ |
| Etiqueta QR do item | `200 image/png` ✅ |

### 📌 Decisões desta etapa
- URLs com query params refletem **apenas** os parâmetros habilitados; os demais
  ficam como `disabled: true` (exigência do lint v3).
- A collection não chama Celery: a pasta 6 documenta os comandos e confere o
  resultado no banco.
- Senhas demo permanecem apenas locais; `admin_password` continua vazio no
  versionamento.

### ⏭️ Próximos passos
1. Revisar envio de notificações via Celery quando o broker estiver disponível.
2. Avaliar exemplos salvos (`.resources/*.resources/examples`) para o front.

## 🗓️ 2026-11-10 — Healthchecks, CI e notificações push assíncronas

### 🎯 Objetivo
Fechar dois pré-requisitos de produção que não dependiam do front: monitorar a
saúde da aplicação (Docker/balanceador) e tirar o envio de notificações do
processo web, com suporte real a Web Push.

### 🧩 Healthchecks
| Rota | Tipo | Comportamento |
| :--- | :--- | :--- |
| `GET /health/` | liveness | Responde `{"status": "ok"}` sem tocar em banco/cache |
| `GET /health/ready/` | readiness | Testa banco + cache; `503` com o detalhe de quem falhou |

Views Django simples (sem JWT e sem throttle do DRF), em `src/config/health.py`,
com testes em `src/config/tests/test_health.py`.

### 🔔 Notificações + push
- Novo app `apps.notifications` com `PushSubscription` (endpoint único por
  navegador, chaves `p256dh`/`auth`, ativação e último uso).
- Rotas `GET/POST /api/notifications/subscriptions/` e
  `DELETE /api/notifications/subscriptions/{id}/` (só as do próprio usuário).
- `services/push_service.py` entrega Web Push com VAPID via `pywebpush` e trata
  inscrição expirada (`404/410` desativa) e falha transitória (mantém ativa).
- `notification_service._deliver_push` passou a enviar de verdade; `dispatch`
  usa a task `notifications.send` quando `NOTIFICATIONS_ASYNC_ENABLED=True`,
  com fallback síncrono se o broker estiver fora.
- Novas variáveis: `NOTIFICATIONS_ASYNC_ENABLED`, `VAPID_PUBLIC_KEY`,
  `VAPID_PRIVATE_KEY`, `VAPID_ADMIN_EMAIL`; `pywebpush==2.5.0` em
  `requirements.txt`.

### ⚙️ CI (GitHub Actions)
`.github/workflows/ci.yml` com dois jobs:
- **lint**: `ruff check src` e `black --check src`;
- **testes e schema**: Postgres 16 + Redis 7, `manage.py check`,
  `makemigrations --check --dry-run`, `spectacular --validate --fail-on-warn`
  e `pytest`.
O drift antigo de `ruff`/`black` em `src/security/` foi corrigido para o CI
nascer verde.

### ✅ Validações
| Verificação | Resultado |
| :--- | :--- |
| `pytest` completo | **270 passed** |
| `ruff check src` | limpo |
| `black --check src` | 124 arquivos sem alteração |
| `manage.py check` | sem issues |
| `makemigrations --check --dry-run` | sem drift |
| `spectacular --validate --fail-on-warn` | 0 warnings, 0 errors |

### 🧠 Decisões desta etapa
- `NOTIFICATIONS_ASYNC_ENABLED` tem default `not DEBUG`: síncrono em
  desenvolvimento/testes, assíncrono em produção.
- Push é opcional: sem VAPID completo o serviço devolve `skipped` e registra no
  log, sem quebrar a operação de negócio.
- O CI usa PostgreSQL (não SQLite) para se aproximar do ambiente real.

### ➡️ Próximos passos
1. Compose de produção (gunicorn, collectstatic, nginx, `DEBUG=False`).
2. Seed de demonstração e exemplos de resposta na collection Postman.

## 🗓️ 2026-11-10 — Compose de produção

### 🎯 Objetivo
Transformar o ambiente Docker em algo publicável: gunicorn no lugar do
`runserver`, arquivos estáticos coletados, nginx na entrada e segredos/portas
fechados.

### 🧩 Arquivos criados/alterados
| Arquivo | Conteúdo |
| :--- | :--- |
| `docker-compose.prod.yml` | `nginx`, `web` (gunicorn), `migrate`, `worker`, `beat`, `db`, `redis` |
| `docker/nginx.conf` | Proxy para `web:8000`, `/static/`, `/media/` e `/health/` |
| `.env.production.example` | Modelo de ambiente de produção (segredos em branco) |
| `.gitignore` / `.dockerignore` | Liberam `!.env.production.example` |

### ⚙️ Decisões
- A imagem de produção usa `INSTALL_DEV=false` (sem pytest/ruff/black).
- O serviço `migrate` roda `migrate`, `setup_periodic_tasks` e `collectstatic`
  antes de `web`/`worker`/`beat`; o `web` só inicia com ele concluído.
- PostgreSQL e Redis **não** publicam portas; o Redis exige `REDIS_PASSWORD`.
- Apenas o nginx publica `${HTTP_PORT:-80}`; o healthcheck do `web` usa
  `GET /health/` e o nginx espera o `web` ficar saudável.
- `X-Forwarded-Proto` é preservado de um proxy TLS à frente (map no nginx),
  evitando loop de `SECURE_SSL_REDIRECT`.
- `client_max_body_size 12m` no nginx (upload limitado a 5 MB na aplicação).
- `/media/` é servido pelo nginx com `autoindex off`.

### ✅ Validações
| Verificação | Resultado |
| :--- | :--- |
| `docker compose --env-file .env.production -f docker-compose.prod.yml config --quiet` | válido |
| Imagem build com `INSTALL_DEV=false` | previsto no compose (Docker daemon não estava ativo) |

### ➡️ Próximos passos
1. Seed de demonstração e exemplos de resposta na collection Postman.

<!-- ===================================================================== -->
<!-- NOVAS ENTRADAS DEVEM SER ADICIONADAS ACIMA DESTA LINHA               -->
<!-- ===================================================================== -->

