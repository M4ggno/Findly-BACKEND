"""
Configurações globais do Findly Backend.

Todas as configurações do Django ficam centralizadas neste módulo. Valores
sensíveis ou que variam por ambiente são lidos de variáveis de ambiente
(ver ``.env.example``) através do ``django-environ``.

Sumário
-------
1.  Caminhos base
2.  Variáveis de ambiente
3.  Segurança / núcleo do Django
4.  Aplicações instaladas
5.  Middlewares
6.  Roteamento e templates
7.  Banco de dados (PostgreSQL)
8.  Autenticação e senhas
9.  Django REST Framework / JWT / OpenAPI
10. Internacionalização
11. Cache (Redis)
12. Celery (Redis) e e-mail
13. Arquivos estáticos e mídia
14. Logging
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import environ

# ===========================================================================
# 1. Caminhos base
# ===========================================================================
# Este arquivo está em `<raiz>/src/config/settings.py`.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src"  # Adicionado ao PYTHONPATH (manage.py / Docker)

# ===========================================================================
# 2. Variáveis de ambiente
# ===========================================================================
env = environ.Env()

_env_file = PROJECT_ROOT / ".env"
if _env_file.exists():
    environ.Env.read_env(_env_file)

# ===========================================================================
# 3. Segurança / núcleo do Django
# ===========================================================================
SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "0.0.0.0"]
)

# ===========================================================================
# 4. Aplicações instaladas
# ===========================================================================
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "simple_history",
    "django_celery_beat",
    "django_celery_results",
]

# Infraestrutura transversal (não são apps de domínio).
INFRA_APPS = [
    # Honeypot + proteção do admin; registrado para expor o management command
    # `honeypot_report`.
    "security",
]

# Apps de domínio do Findly. Os demais serão habilitados nas próximas etapas.
LOCAL_APPS = [
    "apps.users",
    "apps.authentication",
    # "apps.items",
    # "apps.operations",
    # "apps.audit",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + INFRA_APPS + LOCAL_APPS

if DEBUG:
    INSTALLED_APPS += ["django_extensions"]

# ===========================================================================
# 5. Middlewares
# ===========================================================================
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Barra cedo requisições de IPs sinalizados pelo honeypot.
    "security.middleware.HoneypotBlockMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Registra o usuário da requisição nos modelos com histórico (auditoria).
    "simple_history.middleware.HistoryRequestMiddleware",
]

# ===========================================================================
# 6. Roteamento e templates
# ===========================================================================
ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [PROJECT_ROOT / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ===========================================================================
# 7. Banco de dados (PostgreSQL)
# ===========================================================================
# Aceita DATABASE_URL; caso ausente, monta a URL a partir das variáveis
# POSTGRES_*. Isso permite rodar local (localhost) e no Docker (db) sem alterar
# o código — apenas o ambiente.
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=(
            f"postgres://{env('POSTGRES_USER', default='findly')}:"
            f"{env('POSTGRES_PASSWORD', default='findly')}@"
            f"{env('POSTGRES_HOST', default='localhost')}:"
            f"{env('POSTGRES_PORT', default='5432')}/"
            f"{env('POSTGRES_DB', default='findly')}"
        ),
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
# Evita que comandos pendurem indefinidamente quando o banco está indisponível.
if DATABASES["default"]["ENGINE"].endswith("postgresql"):
    DATABASES["default"].setdefault("OPTIONS", {}).setdefault(
        "connect_timeout", env.int("DB_CONNECT_TIMEOUT", default=5)
    )

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ===========================================================================
# 8. Autenticação e senhas
# ===========================================================================
# Modelo de usuário customizado (login por e-mail + papéis: Usuário Comum,
# Operador de Ponto de Coleta, Administrador). Definido ANTES da primeira
# migração — trocar depois exigiria recriar o banco.
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Exige confirmação de e-mail antes do primeiro login (a conta nasce inativa e
# é ativada em `/api/auth/verify-email/`).
AUTH_REQUIRE_EMAIL_VERIFICATION = env.bool(
    "AUTH_REQUIRE_EMAIL_VERIFICATION", default=True
)
# Validade dos tokens de uso único, em segundos.
EMAIL_VERIFICATION_TIMEOUT = env.int("EMAIL_VERIFICATION_TIMEOUT", default=86400)
# Redefinição de senha com expiração curta (requisito do README).
PASSWORD_RESET_TIMEOUT = env.int("PASSWORD_RESET_TIMEOUT", default=3600)

# ===========================================================================
# 9. Django REST Framework / JWT / OpenAPI
# ===========================================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": env.int("API_PAGE_SIZE", default=20),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", default="60/min"),
        "user": env("THROTTLE_USER", default="1000/day"),
        # Escopos das rotas de autenticação (proteção contra força bruta).
        "auth": env("THROTTLE_AUTH", default="20/min"),
        "register": env("THROTTLE_REGISTER", default="5/hour"),
        "password_reset": env("THROTTLE_PASSWORD_RESET", default="5/hour"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=30)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Findly API",
    "DESCRIPTION": (
        "API do Findly — plataforma centralizada de gestão de achados e perdidos."
    ),
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
}

# --- CORS -------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000", "http://localhost:8080"],
)
CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", default=True)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# --- Admin seguro + Honeypot -------------------------------------------------
# O Django Admin NÃO fica em /admin/ (o caminho mais atacado). Ele é movido para
# um caminho secreto (DJANGO_ADMIN_URL) e o clássico /admin/ vira um honeypot que
# registra as tentativas. Gere um caminho aleatório com: make gen-secret
DJANGO_ADMIN_URL = env("DJANGO_ADMIN_URL", default="painel-interno").strip("/") + "/"

HONEYPOT_ENABLED = env.bool("HONEYPOT_ENABLED", default=True)
# "Tarpit": atraso (segundos) imposto a quem cai na isca (0 = desativado).
HONEYPOT_DELAY_SECONDS = env.float("HONEYPOT_DELAY_SECONDS", default=0.0)
# Nº de acessos que faz um IP entrar na blocklist; 0 desativa o bloqueio.
HONEYPOT_BLOCK_THRESHOLD = env.int("HONEYPOT_BLOCK_THRESHOLD", default=5)
# Tempo (segundos) que conta para o limite e para a expiração da blocklist.
HONEYPOT_BLOCK_TTL_SECONDS = env.int("HONEYPOT_BLOCK_TTL_SECONDS", default=86400)
# Tamanho máximo do histórico de eventos mantido no Redis.
HONEYPOT_MAX_EVENTS = env.int("HONEYPOT_MAX_EVENTS", default=1000)
# Registra o usuário tentado no login falso (a senha vira hash + tamanho).
HONEYPOT_LOG_CREDENTIALS = env.bool("HONEYPOT_LOG_CREDENTIALS", default=True)
# Guarda a senha tentada em texto puro (default: apenas sha256 + tamanho).
HONEYPOT_CAPTURE_PASSWORD_PLAINTEXT = env.bool(
    "HONEYPOT_CAPTURE_PASSWORD_PLAINTEXT", default=False
)
# IPs que nunca são bloqueados (evita auto-bloqueio em desenvolvimento).
HONEYPOT_TRUSTED_IPS = env.list(
    "HONEYPOT_TRUSTED_IPS", default=["127.0.0.1", "::1", "localhost"]
)
# Se True, bloqueia também faixas privadas/loopback (cuidado: pode se auto-bloquear).
HONEYPOT_BLOCK_PRIVATE_IPS = env.bool("HONEYPOT_BLOCK_PRIVATE_IPS", default=False)
# Caminhos "isca" comuns varridos por scanners (registra e devolve 404).
HONEYPOT_EXTRA_PATHS = env.list(
    "HONEYPOT_EXTRA_PATHS",
    default=[
        "wp-admin",
        "wp-login.php",
        "phpmyadmin",
        ".env",
        "admin.php",
        "config.php",
    ],
)

# ===========================================================================
# 10. Internacionalização
# ===========================================================================
LANGUAGE_CODE = "pt-br"
TIME_ZONE = env("DJANGO_TIME_ZONE", default="America/Sao_Paulo")
USE_I18N = True
USE_TZ = True

# ===========================================================================
# 11. Cache (Redis)
# ===========================================================================
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": "findly",
        "TIMEOUT": 300,
    }
}

# ===========================================================================
# 12. Celery (Redis) e e-mail
# ===========================================================================
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND", default="redis://localhost:6379/2"
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_RESULT_EXTENDED = True
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Findly <no-reply@findly.local>")

# URLs usadas nos e-mails transacionais. O front-end recebe `uid` e `token` na
# query string; os mesmos valores também vão no corpo do e-mail.
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000").rstrip("/")
EMAIL_VERIFICATION_URL = env(
    "EMAIL_VERIFICATION_URL", default=f"{FRONTEND_URL}/verificar-email"
)
PASSWORD_RESET_URL = env(
    "PASSWORD_RESET_URL", default=f"{FRONTEND_URL}/redefinir-senha"
)

# ===========================================================================
# 13. Arquivos estáticos e mídia
# ===========================================================================
STATIC_URL = env("STATIC_URL", default="/static/")
STATIC_ROOT = PROJECT_ROOT / "staticfiles"

MEDIA_URL = env("MEDIA_URL", default="/media/")
MEDIA_ROOT = PROJECT_ROOT / "media"

# Limite de upload usado pelo Serviço de Fotos.
MAX_UPLOAD_SIZE_MB = env.int("MAX_UPLOAD_SIZE_MB", default=5)
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

# ===========================================================================
# 14. Logging
# ===========================================================================
LOG_DIR = PROJECT_ROOT / "logs"
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except OSError:  # pragma: no cover - sistema de arquivos somente leitura
    pass

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        # Arquivo dedicado a eventos de segurança/honeypot (persistente).
        "security_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "security.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        # Eventos capturados pelo honeypot (acessos ao /admin e iscas).
        "findly.security": {
            "handlers": ["console", "security_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ===========================================================================
# Endurecimento para produção (somente quando DEBUG=False)
# ===========================================================================
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
