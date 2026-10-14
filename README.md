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

---

## 📐 6. Padrões de Código e Convenções da Equipe

1. **Fat Services, Skinny Views:** As `Views` devem apenas receber a requisição, validar o `Serializer` e chamar a camada de **Regras de Negócio / Serviços**.
2. **Transações Atômicas:** Toda operação que envolva troca de **Custódia** ou **Entrega/Retirada** deve ser encapsulada em `@transaction.atomic`.
3. **Auditoria Inegociável:** Nenhuma alteração de `Status` ou `Custódia` pode ocorrer sem registrar um evento correspondente no módulo de **Histórico / Auditoria**.