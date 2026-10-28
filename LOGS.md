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

<!-- ===================================================================== -->
<!-- NOVAS ENTRADAS DEVEM SER ADICIONADAS ACIMA DESTA LINHA               -->
<!-- ===================================================================== -->

