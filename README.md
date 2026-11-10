# 📦 Findly Backend — System Design & Documentação Oficial

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.x-092E20?style=for-the-badge&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)

O **Findly** é uma plataforma centralizada para gerenciamento inteligente de **achados e perdidos**, projetada para conectar pessoas que perderam pertences a quem os encontrou ou aos pontos de coleta oficiais, garantindo segurança, rastreabilidade de custódia e validação antifraude na devolução.

Este `README.md` atua como o documento vivo de **System Design** do nosso backend, definindo a arquitetura em camadas, o fluxo de dados, as regras de negócio e a infraestrutura em Docker.

---

## 🗺️ 1. Arquitetura e Fluxo do Sistema (System Design)

O backend foi projetado em uma arquitetura em camadas (**Layered Architecture**) com separação clara entre controle de rotas, domínio, regras de negócio, serviços internos e persistência auditável.

> 💡 *Dica: Salve a imagem gerada da arquitetura na pasta `docs/` do repositório para exibi-la abaixo:*
> `![Fluxo do Findly Backend](./docs/findly-architecture.png)`

```text
                        FINDLY BACKEND
                              │
                              ▼
                    DJANGO + PYTHON (Core)
                    Backend Principal / API
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   AUTENTICAÇÃO           USUÁRIOS                ITENS
        │                     │              ┌──────┼───────┐
        ▼                     ▼              ▼      ▼       ▼
   Login/Logout            Perfil         Achados Perdidos Status
   Cadastro                Dados             │      │       │
   Recuperação                │              │      │       │
        │                     │              │      │       │
        └─────────────────────┼──────────────┴──────┘       │
                              │                             │
                              ▼                             ▼
                      REGRAS DE NEGÓCIO ◄───────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
    CUSTÓDIA              ENTREGAS /             PONTOS
    DE ITENS              RETIRADAS             DE COLETA
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                     SERVIÇOS DO DJANGO
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
     QR CODE                FOTOS             NOTIFICAÇÕES
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                         POSTGRESQL
                              │
                              ▼
                    HISTÓRICO / AUDITORIA
```

---

## 🛠️ 2. Stack Tecnológica e Decisões Arquiteturais

| Camada / Componente | Tecnologia | Justificativa no System Design |
| :--- | :--- | :--- |
| **Core & API** | Python 3.11+ & Django 5.x (DRF) | Rapidez no desenvolvimento, ORM seguro contra SQL Injection e ecossistema maduro para APIs RESTful. |
| **Autenticação** | JWT (`simplejwt`) + Django Auth | Autenticação *stateless* segura para consumo via front-end web e aplicativo mobile. |
| **Banco de Dados** | PostgreSQL 15+ | Conformidade ACID indispensável para transações de troca de custódia e integridade relacional. |
| **Processamento de Mídia** | Pillow (`PIL`) | Compressão de imagens, padronização de resolução e remoção de metadados sensíveis (EXIF). |
| **Validação Física** | `python-qrcode` | Geração de códigos únicos para etiquetagem de itens e vouchers de retirada presencial. |
| **Auditoria** | `django-simple-history` / Logs | Rastreabilidade imutável de ponta a ponta sobre quem manipulou cada item ou alterou status. |
| **Infraestrutura** | Docker & Docker Compose | Padronização total entre ambientes de desenvolvimento, homologação e produção. |

---

## ⚙️ 3. Detalhamento das Camadas do Sistema

### 3.1. Núcleo de Entrada (`Django + Python`)
* Recebe todas as requisições HTTP/HTTPS via API REST.
* Aplica middlewares de segurança (CORS, CSRF, Rate Limiting e validação de cabeçalhos).
* Roteia as chamadas para os módulos de domínio correspondentes.

### 3.2. Módulos de Domínio
1. **Autenticação (`auth`):**
   * **Login/Logout:** Emissão de pares de tokens (`access` e `refresh`) e invalidação via *blacklist*.
   * **Cadastro:** Registro com validação de credenciais e verificação de conta.
   * **Recuperação:** Redefinição de senha via token temporário com tempo de expiração curto.
2. **Usuários (`users`):**
   * **Perfil e Dados:** Dados cadastrais, informações de contato, histórico de itens vinculados e controle de permissões (Usuário Comum, Operador de Ponto de Coleta, Administrador).
3. **Itens (`items`):**
   * **Achados:** Objetos encontrados e cadastrados por usuários ou operadores.
   * **Perdidos:** Alertas abertos por usuários que buscam um pertence.
   * **Status (Máquina de Estados):** Controla o ciclo de vida estrito do objeto dentro da plataforma:
     ```text
     [REPORTADO] ──► [EM_CUSTODIA] ──► [AGUARDANDO_RETIRADA] ──► [DEVOLVIDO]
                          │
                          └──► [EXPIRADO / ENCAMINHADO]
     ```

### 3.3. Regras de Negócio (`Business Logic Layer`)
O núcleo estratégico do Findly isola as validações complexas fora das *views*:
* **Custódia de Itens:** Registra quem detém a posse física do objeto em cada momento (o usuário que encontrou ou um Ponto de Coleta específico). Nenhuma troca de posse ocorre sem registro transacional.
* **Pontos de Coleta:** Gerencia unidades físicas autorizadas (ex: recepções, guaritas, centrais de atendimento), incluindo capacidade, horários de funcionamento e operadores responsáveis.
* **Entregas / Retiradas:** Orquestra o processo de reivindicação (*claim*), exigindo validação de propriedade pelo dono antes de liberar a retirada mediante leitura do QR Code.

### 3.4. Serviços do Django (`Service Layer`)
Módulos utilitários desacoplados que são acionados pelas regras de negócio:
* **Serviço de QR Code:**
  * Gera etiqueta de identificação para colar no item físico ao dar entrada em um Ponto de Coleta.
  * Gera o QR Code de autorização temporária para o proprietário apresentar no ato da retirada.
* **Serviço de Fotos:**
  * Valida extensão e tamanho máximo, comprime a imagem para otimizar armazenamento e remove dados de geolocalização (EXIF) por segurança.
* **Serviço de Notificações:**
  * Dispara alertas por e-mail/push quando há *match* entre um item perdido e um achado, quando um item muda de custódia ou quando uma entrega é finalizada.

### 3.5. Persistência e Auditoria (`Data & Audit Layer`)
* **PostgreSQL:** Armazena os dados relacionais utilizando transações atômicas (`transaction.atomic()`), garantindo que uma falha na geração do histórico ou do QR Code reverta a operação inteira.
* **Histórico / Auditoria:** Mantém uma trilha de auditoria (*Audit Trail*) contendo:
  * `item_id`, `acao_realizada`, `status_anterior`, `status_novo`, `usuario_responsavel`, `ponto_coleta_id` e `timestamp`.

---

## 📂 4. Estrutura de Diretórios do Projeto

```text
findly-backend/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── requirements.txt
├── manage.py
├── docs/
│   └── findly-architecture.png
└── src/
    ├── config/              # Configurações globais do Django (settings, urls, wsgi)
    ├── apps/
    │   ├── authentication/  # Login, Logout, Cadastro, Recuperação
    │   ├── users/           # Perfil e Dados de Usuários
    │   ├── items/           # Achados, Perdidos e Máquina de Status
    │   ├── operations/      # Regras de Negócio: Custódia, Entregas/Retiradas, Pontos de Coleta
    │   └── audit/           # Histórico e Logs de Auditoria
    └── services/            # Serviços transversais do Django
        ├── qrcode_service.py
        ├── photo_service.py
        └── notification_service.py
```

---

## 🐳 5. Infraestrutura com Docker

O ambiente é inteiramente orquestrado via **Docker** e **Docker Compose**, garantindo paridade entre desenvolvimento e produção.

### Arquitetura de Containers
* **`findly_web` (Django + Python):** Container da aplicação rodando sobre `python:3.11-slim`. Aguarda o banco estar saudável, aplica as migrações e inicializa o servidor.
* **`findly_db` (PostgreSQL):** Container oficial `postgres:15-alpine` com *healthcheck* configurado.
* **Volumes Persistentes:**
  * `postgres_data`: Garante que o banco de dados e o histórico de auditoria persistam mesmo se os containers forem recriados.
  * `media_volume`: Armazena as fotos dos itens e os QR Codes gerados.
  * `static_volume`: Armazena arquivos estáticos do Django Admin e Swagger/OpenAPI.

### Como Executar o Projeto com Docker

1. **Clone o repositório e configure as variáveis de ambiente:**
   ```bash
   git clone https://github.com/sua-organizacao/findly-backend.git
   cd findly-backend
   cp .env.example .env
   ```

2. **Suba os containers em segundo plano:**
   ```bash
   docker compose up -d --build
   ```

3. **Acompanhe os logs da aplicação:**
   ```bash
   docker compose logs -f web
   ```

4. **Comandos úteis de manutenção no container:**
   ```bash
   # Criar superusuário para o Django Admin
   docker compose exec web python manage.py createsuperuser

   # Rodar a suíte de testes automatizados
   docker compose exec web python manage.py test
   ```

### Healthchecks

Rotas públicas (sem JWT e sem throttle) usadas pelo Docker e pelo balanceador:

| Rota | Tipo | O que verifica |
| :--- | :--- | :--- |
| `GET /health/` | liveness | Apenas se o processo web está vivo; não toca em banco/cache |
| `GET /health/ready/` | readiness | Banco de dados e cache; devolve `503` com o detalhe quando algo falha |

```bash
curl -fsS http://localhost:8000/health/
curl -fsS http://localhost:8000/health/ready/
```

### Produção (`docker-compose.prod.yml`)

O compose de produção troca o servidor de desenvolvimento por **gunicorn**,
constrói a imagem sem ferramentas de dev, publica apenas o **nginx** e protege o
Redis com senha.

| Serviço | Papel |
| :--- | :--- |
| `nginx` | Entrada HTTP, serve `/static/` e `/media/` e faz proxy para o gunicorn |
| `web` | Django via gunicorn (`GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`) |
| `migrate` | One-shot: `migrate` + `setup_periodic_tasks` + `collectstatic` |
| `worker` / `beat` | Celery (notificações assíncronas e tarefas periódicas) |
| `db` / `redis` | PostgreSQL 16 e Redis 7, **sem portas publicadas** |

1. **Crie o arquivo de ambiente e preencha os segredos:**
   ```bash
   cp .env.production.example .env.production
   # edite DJANGO_SECRET_KEY, POSTGRES_PASSWORD, REDIS_PASSWORD, hosts, SMTP, VAPID...
   ```

2. **Suba a stack** (o `--env-file` é obrigatório: o compose usa essas variáveis
   na interpolação):
   ```bash
   docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
   ```

3. **Acompanhe a subida e os logs:**
   ```bash
   docker compose --env-file .env.production -f docker-compose.prod.yml ps
   docker compose --env-file .env.production -f docker-compose.prod.yml logs -f web
   ```

4. **Crie o superusuário do admin secreto:**
   ```bash
   docker compose --env-file .env.production -f docker-compose.prod.yml \
     exec web python manage.py createsuperuser
   ```

**Checklist de produção**

- `DJANGO_DEBUG=False` (ativa `SECURE_SSL_REDIRECT`, HSTS e cookies seguros).
- Termine o **TLS** no nginx ou em um proxy à frente e envie
  `X-Forwarded-Proto: https`; sem isso o redirect para HTTPS entra em loop.
- Ajuste `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` e `CSRF_TRUSTED_ORIGINS`
  para os domínios reais.
- `MAX_UPLOAD_SIZE_MB` é 5; o nginx aceita até 12 MB por requisição.
- O `/media/` é servido pelo nginx; não habilite listagem de diretório.
- O healthcheck do serviço `web` usa `GET /health/`; o `nginx` só sobe quando o
  `web` está saudável.
- Backups: `postgres_data` (banco), `media_volume` (fotos/QR) e
  `static_volume` (regenerável via `collectstatic`).

---

## 📐 6. Padrões de Código e Convenções da Equipe

1. **Fat Services, Skinny Views:** As `Views` devem apenas receber a requisição, validar o `Serializer` e chamar a camada de **Regras de Negócio / Serviços**.
2. **Transações Atômicas:** Toda operação que envolva troca de **Custódia** ou **Entrega/Retirada** deve ser encapsulada em `@transaction.atomic`.
3. **Auditoria Inegociável:** Nenhuma alteração de `Status` ou `Custódia` pode ocorrer sem registrar um evento correspondente no módulo de **Histórico / Auditoria**.

### Integração contínua

O workflow `.github/workflows/ci.yml` roda em todo push para `main` e em pull
requests, com dois jobs:

| Job | Verificações |
| :--- | :--- |
| `lint` | `ruff check src` e `black --check src` |
| `test` | PostgreSQL 16 + Redis 7, `manage.py check`, `makemigrations --check --dry-run`, `spectacular --validate --fail-on-warn` e `pytest` |

Para reproduzir localmente:

```bash
ruff check src
black --check src
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py spectacular --validate --fail-on-warn
pytest
```

---

## 🧪 7. Coleção Postman (Autenticação e Front-end)

Os artefatos ficam versionados em `postman/` (formato v3, um arquivo por
requisição):

| Caminho | Conteúdo |
| :--- | :--- |
| `postman/collections/Findly API/` | 49 requisições em 7 pastas: autenticação (8), usuários (5), itens (12), operações (14), auditoria (3), manutenção (4) e notificações (3), com 10 exemplos de resposta salvos |
| `postman/environments/Findly Local.environment.yaml` | `base_url`, credenciais de demonstração e variáveis encadeadas (`found_code`, `point_id`, `claim_id`, `withdrawal_token`, `subscription_id`, `push_*`…) |

**Como usar**

1. Suba a API: `docker compose up -d --build`.
2. No Postman, importe a pasta `postman/collections/Findly API` e o environment
   `postman/environments/Findly Local.environment.yaml`.
3. Selecione o environment **Findly Local**.
4. Siga o roteiro da descrição da collection: **Cadastro → Verificar e-mail →
   Login → Meu perfil → Renovar token → Logout**.

Os scripts das requisições salvam `access_token`, `refresh_token` e `user_id` no
environment automaticamente. Em desenvolvimento, os e-mails de verificação e de
reset aparecem no console (`docker compose logs -f web`).

**Fluxo completo (itens → operações → auditoria)**

| Pasta | O que demonstrar |
| :--- | :--- |
| `1 - Autenticacao` | Cadastro, verificação, login, refresh rotativo e logout |
| `2 - Usuarios` | Perfil próprio e gestão de contas (admin) |
| `3 - Itens` | Cadastro do achado/perdido, edição, transições, fotos |
| `4 - Operacoes` | Ponto de coleta, transferência, claim, aprovação e retirada por QR |
| `5 - Auditoria` | Histórico do item e trilha global (admin) |
| `6 - Manutencao` | Itens/alertas expirados, claims recusadas e eventos automáticos |
| `7 - Notificacoes` | Inscrições de Web Push do usuário (listar, registrar e remover) |

Os scripts encadeiam os IDs: cadastrar o achado salva `found_code`; criar/listar
um ponto salva `point_id`; abrir/listar um claim salva `claim_id`; aprovar salva
`withdrawal_token`, usado na confirmação da retirada. O token é então limpo do
environment.

Os exemplos salvos (aba **Examples** de cada requisição) mostram a resposta real
esperada — por exemplo o achado em `REPORTADO`, o claim em `PENDING`/`APPROVED`
com o QR de 24 h e a retirada concluída em `DEVOLVIDO`.

### 7.1. Dados de demonstração (`seed_demo`)

Para ter contas e itens prontos sem montar o fluxo à mão:

```bash
# Local (DEBUG=True)
docker compose exec web python manage.py seed_demo

# Redefinir as senhas das contas demo
docker compose exec web python manage.py seed_demo --reset-passwords
```

O comando é **idempotente**: pode rodar quantas vezes quiser — usuários são
buscados por e-mail, pontos por nome e itens/alertas por código fixo; nada é
apagado nem tem o status resetado. Em `DEBUG=False` ele se recusa a rodar sem
`--force` (as senhas demo são conhecidas).

| Conta | E-mail | Papel |
| :--- | :--- | :--- |
| Demo | `demo@findly.local` | comum |
| Reivindicante | `reivindicante@findly.local` | comum |
| Operador | `operador@findly.local` | operador de ponto |
| Administrador | `admin@findly.local` | admin (`is_staff`/`is_superuser`) |

Senha padrão: `Findly@2026!` (troque com `--password`). Códigos fixos:

| Código | O que representa |
| :--- | :--- |
| `DEMOACHADO` | achado `EM_CUSTODIA` na Portaria do Prédio A |
| `DEMOCHAVES` | achado `REPORTADO` (ainda com o autor) |
| `DEMOCARTEI` | achado `AGUARDANDO_RETIRADA`, claim aprovado e QR emitido |
| `DEMOPERDID` | alerta de perda compatível com `DEMOACHADO` |
| `DEMOALERTA` | alerta de perda sem match |

O seed cria 2 pontos de coleta e silencia e-mail/push, para não disparar
notificações durante a carga.

> A pasta `6 - Manutencao` não chama tarefas: notificações e expiração são
> efeitos do Celery/e-mail. Ela traz as requisições de **verificação** e os
> comandos para rodar cada tarefa (ver descrição da pasta e README, seção 12).

Também é possível executar pela CLI sem abrir o Postman:

```bash
postman collection run "postman/collections/Findly API" \
  -e "postman/environments/Findly Local.environment.yaml"
```

> As credenciais do environment são **exclusivas para desenvolvimento local**.

---

## 🧾 8. API de Itens (achados, perdidos e fotos)

Todas as rotas exigem `Authorization: Bearer <access>` e usam o `public_code`
(10 caracteres, sem letras ambíguas) em vez do ID sequencial.

### 8.1. Achados — `/api/items/found/`

| Método | Rota | Quem pode | Descrição |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/items/found/` | autenticado | Lista com paginação e filtros |
| `POST` | `/api/items/found/` | autenticado | Cadastra um achado (`REPORTADO`) |
| `GET` | `/api/items/found/{code}/` | autenticado | Detalhe + fotos |
| `PUT/PATCH` | `/api/items/found/{code}/` | autor (só `REPORTADO`), operador, admin | Edita os dados |
| `POST` | `/api/items/found/{code}/status/` | operador, admin | Aplica uma transição válida |
| `POST` | `/api/items/found/{code}/photos/` | autor, operador, admin | Upload de foto (multipart) |
| `DELETE` | `/api/items/found/{code}/photos/{id}/` | autor, operador, admin | Remove a foto |

**Corpo do cadastro/edição**

```json
{
  "title": "Carteira preta",
  "description": "Carteira de couro com documentos.",
  "category": "carteiras",
  "found_at": "2026-11-09T18:30:00Z",
  "found_location": "Recepção do prédio A"
}
```

Categorias: `eletronicos`, `documentos`, `vestuario`, `chaves`, `carteiras`,
`moveis`, `outros`.

**Filtros de listagem:** `status`, `category`, `found_after`, `found_before`,
`mine=true`, `search` (título, descrição, local e código) e `ordering`
(`created_at`, `found_at`, `title`, `status`).

### 8.2. Máquina de estados

```text
REPORTADO ──► EM_CUSTODIA ──► AGUARDANDO_RETIRADA ──► DEVOLVIDO
     │              │                    │
     └──────────────┴────────────────────┴──► EXPIRADO / ENCAMINHADO
```

- Estados finais não aceitam novas transições (`400`).
- Saltos inválidos (ex.: `REPORTADO → DEVOLVIDO`) retornam `400`.
- O status **não** é editável via `PATCH`: use `POST .../status/`.
- A transição roda em `transaction.atomic` (`apps/items/services.py`).

### 8.3. Perdidos — `/api/items/lost/`

| Método | Rota | Quem pode | Descrição |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/items/lost/` | autenticado | Lista com filtros (`status`, `category`, `mine`, datas, busca) |
| `POST` | `/api/items/lost/` | autenticado | Abre um alerta (`ABERTO`) |
| `GET` | `/api/items/lost/{code}/` | autenticado | Detalhe |
| `PUT/PATCH` | `/api/items/lost/{code}/` | dono (enquanto `ABERTO`), admin | Edita |
| `POST` | `/api/items/lost/{code}/cancel/` | dono, admin | Marca como `CANCELADO` |

### 8.4. Fotos

- Formatos: **JPEG, PNG e WebP**; máximo **5 MB**.
- O backend corrige a orientação, limita o maior lado a **1600 px**, recomprime em
  JPEG (qualidade 85) e **remove todo o EXIF** (geolocalização, câmera etc.).
- As fotos ficam em `media/items/<public_code>/`.

### 8.5. Privacidade

O autor é exposto apenas como `{"id", "full_name"}` — e-mail e telefone nunca
aparecem nas respostas de itens. A retirada será negociada pelo fluxo de
*custódia/claim* do app `operations` (próxima etapa).

---

## 🧾 9. Auditoria e Histórico

Toda criação de item e **toda** mudança de status/custódia gera um evento na
trilha de auditoria, **na mesma transação** da operação original. Se o registro
do evento falhar, a operação inteira é revertida (README, seção 3.5).

### 9.1. Modelo imutável — `AuditEvent`

| Campo | Descrição |
| :--- | :--- |
| `item` | Item auditado (`PROTECT`; o histórico nunca perde a referência) |
| `action` | `CREATED`, `STATUS_CHANGED`, `CUSTODY_TRANSFERRED`, `CLAIM_APPROVED`, `CLAIM_REJECTED`, `CLAIM_CANCELLED`, `WITHDRAWAL_CONFIRMED` |
| `previous_status` / `new_status` | Transição registrada (vazio na criação) |
| `responsible` | Quem executou (`null` em ações automáticas, como expiração) |
| `collection_point` | Ponto de coleta envolvido no evento (quando aplicável) |
| `metadata` | Contexto adicional (ponto de coleta, claim, QR etc.) |
| `created_at` | Timestamp do evento |

- `save()` em um evento existente e `delete()` levantam `ValueError`.
- O admin é **somente leitura**: sem criação, edição ou exclusão.
- Ordenação padrão: mais recente primeiro.

### 9.2. Rotas

| Método | Rota | Quem pode | Descrição |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/items/found/{code}/history/` | autor, operador, admin | Histórico completo do item (sem paginação) |
| `GET` | `/api/audit/` | admin | Trilha global, paginada |
| `GET` | `/api/audit/{id}/` | admin | Detalhe de um evento |

**Filtros de `/api/audit/`:** `item` (código público), `action`,
`collection_point`, `date_from`, `date_to`, `search` (código/título do item,
nome do responsável/ponto) e `ordering` (`created_at`, `action`).

### 9.3. Eventos automáticos

Criação: `CREATED` (`REPORTADO`). Transições: `STATUS_CHANGED` com
`previous_status` e `new_status` preenchidos. Custódia, claims e retirada são
registrados pelo app `operations` (`CUSTODY_TRANSFERRED`, `CLAIM_APPROVED`,
`CLAIM_REJECTED`, `CLAIM_CANCELLED`, `WITHDRAWAL_CONFIRMED`).

---

## 🏢 10. Operações (pontos de coleta, custódia, claims e retirada)

### 10.1. Pontos de coleta — `/api/operations/points/`

| Método | Rota | Quem pode | Descrição |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/operations/points/` | autenticado | Lista com busca e filtros |
| `POST` | `/api/operations/points/` | admin | Cria um ponto |
| `GET` | `/api/operations/points/{id}/` | autenticado | Detalhe |
| `PUT/PATCH` | `/api/operations/points/{id}/` | admin | Edita (use `is_active=false` para desativar) |

Campos: `name`, `address`, `opening_hours`, `capacity` (vazio = ilimitado),
`operators` (ids de operadores/admins), `is_active`. A leitura inclui
`operators_display`, `occupancy` e `has_capacity`.
**Filtros:** `is_active`, `operator`, `has_capacity`, `search`, `ordering`.

### 10.2. Custódia — `/api/operations/items/found/{code}/`

| Método | Rota | Quem pode | Descrição |
| :--- | :--- | :--- | :--- |
| `GET` | `.../custody/` | autor, operador, admin | Histórico de custódia |
| `POST` | `.../custody/transfer/` | operador, admin | Transfere para um ponto |
| `GET` | `.../label/` | autor, operador, admin | Etiqueta QR (PNG) do item |

- O cadastro do achado abre a custódia inicial com quem o registrou.
- A transferência fecha o registro aberto e abre um novo no ponto de coleta.
- Operador só transfere para ponto do qual é responsável; a capacidade é
  validada; `REPORTADO → EM_CUSTODIA` ocorre na mesma transação.
- Toda transferência grava `CUSTODY_TRANSFERRED` com o ponto e o responsável.

### 10.3. Claims — `/api/operations/`

| Método | Rota | Quem pode | Descrição |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/operations/items/found/{code}/claims/` | autenticado | Próprios claims (operador/admin veem todos) |
| `POST` | `/api/operations/items/found/{code}/claims/` | autenticado | Abre uma reivindicação |
| `GET` | `/api/operations/claims/` | autenticado | Lista (ver acima) |
| `GET` | `/api/operations/claims/{id}/` | autor, operador, admin | Detalhe |
| `POST` | `/api/operations/claims/{id}/approve/` | operador, admin | Aprova e emite o QR |
| `POST` | `/api/operations/claims/{id}/reject/` | operador, admin | Recusa |
| `POST` | `/api/operations/claims/{id}/cancel/` | autor, admin | Cancela (só pendente) |

Regras: quem cadastrou o achado não pode reivindicá-lo; não há claim duplicado
pendente por usuário/item; item terminal não aceita claim; a aprovação exige o
item em `EM_CUSTODIA` ou `AGUARDANDO_RETIRADA`; aprovar um claim recusa os demais
pendentes do mesmo item.

### 10.4. Retirada via QR — `/api/operations/withdrawals/confirm/`

```json
{ "token": "FINDLY:WITHDRAWAL:<token>" }
```

- O QR é emitido na aprovação do claim, vale **24 h** e é de **uso único**.
- A confirmação exige operador/admin, move o item para `DEVOLVIDO`, fecha a
  custódia ativa e grava `WITHDRAWAL_CONFIRMED` na mesma transação.
- Token inválido, expirado, já utilizado ou de claim não aprovado retorna `400`.
- `metadata` do evento guarda `claim`, `claimant` e `withdrawal`.

---

## 🔔 11. Notificações (e-mail e push)

O serviço transversal `src/services/notification_service.py` dispara alertas
quando há **match** entre perdido e achado, quando o item **muda de custódia**,
quando a **retirada é liberada** e quando a **entrega é concluída**.

### 11.1. Eventos e destinatários

| Evento | Destinatário | Conteúdo |
| :--- | :--- | :--- |
| Achado compatível com alerta | dono do alerta de perda | item, local, data e link para reivindicar |
| Alerta aberto com achados existentes | dono do alerta | lista de achados compatíveis |
| Transferência para ponto | autor do achado | novo ponto, endereço e horário |
| Claim aprovado | reivindicante | ponto de retirada, validade e QR disponível na conta |
| Retirada confirmada | reivindicante + autor do achado | entrega concluída e histórico |

### 11.2. Regras de match

- Mesma **categoria** em perdido e achado.
- O achado deve ocorrer **depois** da perda e dentro de `MATCH_WINDOW_DAYS`
  (padrão: 30 dias).
- Ao menos uma **palavra significativa** em comum entre título/descrição
  (sem acentos, sem stopwords e com 4+ caracteres).
- Alertas cancelados e achados terminais (`DEVOLVIDO`, `EXPIRADO`,
  `ENCAMINHADO`) são ignorados.
- `MATCH_NOTIFICATION_LIMIT` (padrão: 5) limita as notificações por evento.

### 11.3. Configuração

| Variável | Padrão | Descrição |
| :--- | :--- | :--- |
| `EMAIL_BACKEND` | console | Backend de e-mail do Django |
| `DEFAULT_FROM_EMAIL` | `Findly <no-reply@findly.local>` | Remetente |
| `NOTIFICATIONS_ASYNC_ENABLED` | `not DEBUG` | Envia pelo worker do Celery (há fallback síncrono se o broker falhar) |
| `NOTIFICATIONS_PUSH_ENABLED` | `false` | Habilita o canal de Web Push |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` | vazio | Par VAPID do Web Push (obrigatório com o push ligado) |
| `VAPID_ADMIN_EMAIL` | `admin@findly.local` | Contato exigido no claim VAPID |
| `MATCH_WINDOW_DAYS` | `30` | Janela máxima entre perda e achado |
| `MATCH_NOTIFICATION_LIMIT` | `5` | Máximo de notificações por evento |

- O envio é agendado com `transaction.on_commit`: rollback da operação não
  dispara e-mail/push.
- Com `NOTIFICATIONS_ASYNC_ENABLED=True` a mensagem vai para a task
  `notifications.send` no worker Celery; se o broker estiver fora, o envio cai
  para o processo web em vez de quebrar a operação.
- Falhas de SMTP/push são logadas e **não** interrompem a regra de negócio.
- Em desenvolvimento, `EMAIL_BACKEND` de console imprime a mensagem no terminal.

### 11.4. Web Push

O app `apps.notifications` guarda uma inscrição por navegador/dispositivo
(`PushSubscription`) e o front a registra depois de obter a permissão do
usuário (`PushManager.subscribe()`):

| Rota | Descrição |
| :--- | :--- |
| `GET /api/notifications/subscriptions/` | Lista as inscrições do usuário autenticado |
| `POST /api/notifications/subscriptions/` | Cria/atualiza a inscrição (`endpoint` + `keys.p256dh` + `keys.auth`) |
| `DELETE /api/notifications/subscriptions/{id}/` | Remove uma inscrição do próprio usuário |

- O mesmo `endpoint` reenviado é atualizado, inclusive quando outro usuário
  entra no mesmo navegador.
- O provedor de push responde `404`/`410` quando a inscrição expirou; ela é
  desativada automaticamente (`is_active=False`).
- Sem o par VAPID completo, `services/push_service.py` devolve `skipped` e
  registra no log — o restante do fluxo não é afetado.
- O token do QR de retirada **não** é enviado por e-mail nem por push; o
  reivindicante o obtém autenticado na própria conta.

---

## 🧹 12. Manutenção automática (Celery beat)

Tarefas periódicas registradas em `django_celery_beat` pelo comando
`python manage.py setup_periodic_tasks` (idempotente; roda no serviço `migrate`
do Docker Compose).

| Tarefa | Horário | O que faz |
| :--- | :--- | :--- |
| `apps.items.tasks.expire_found_items` | 03:00 | Itens sem movimentação há `ITEM_EXPIRATION_DAYS` viram `EXPIRADO`; claims pendentes são recusadas com auditoria |
| `apps.items.tasks.expire_lost_reports` | 03:15 | Alertas abertos há `LOST_REPORT_EXPIRATION_DAYS` viram `EXPIRADO` |
| `apps.operations.tasks.cleanup_expired_withdrawal_qrs` | 03:30 | Remove o PNG de QRs expirados há mais de `WITHDRAWAL_QR_RETENTION_DAYS` |

### 12.1. Regras

- A expiração do achado usa `updated_at`: qualquer transferência, mudança de
  status ou decisão renova o prazo.
- A transição para `EXPIRADO` grava `STATUS_CHANGED` com responsável nulo
  (ação automática) e recusa os claims pendentes na mesma transação.
- O registro de `WithdrawalAuthority` **não** é apagado na limpeza do QR: só o
  arquivo é removido e o campo `qr_image` é limpo, preservando o histórico.
- Itens em estado terminal (`DEVOLVIDO`, `EXPIRADO`, `ENCAMINHADO`) e alertas
  já cancelados/expirados não são tocados.

### 12.2. Execução manual

```bash
python manage.py setup_periodic_tasks
python manage.py shell -c "from apps.items.tasks import expire_found_items; print(expire_found_items())"
python manage.py shell -c "from apps.operations.tasks import cleanup_expired_withdrawal_qrs; print(cleanup_expired_withdrawal_qrs())"
```

| Variável | Padrão | Descrição |
| :--- | :--- | :--- |
| `ITEM_EXPIRATION_DAYS` | `90` | Inatividade máxima do achado |
| `LOST_REPORT_EXPIRATION_DAYS` | `90` | Idade máxima do alerta de perda |
| `WITHDRAWAL_QR_RETENTION_DAYS` | `7` | Retenção do PNG após a expiração |

