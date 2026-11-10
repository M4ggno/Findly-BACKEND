"""Roteamento de URLs raiz do Findly Backend.

Expõe o Django Admin (em caminho secreto), o honeypot em ``/admin/``, a
documentação OpenAPI/Swagger, os healthchecks e as rotas de cada app de domínio.
"""

from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from .health import liveness, readiness

urlpatterns = [
    # --- Healthchecks (Docker / balanceador) --------------------------------
    path("health/", liveness, name="health"),
    path("health/ready/", readiness, name="health-ready"),
    # --- Honeypot -----------------------------------------------------------
    # Deve vir ANTES do admin real: transforma o clássico /admin/ (e iscas
    # comuns) em armadilha que registra quem tenta acessá-lo.
    path("", include("security.urls")),
    # --- Administração (caminho secreto) ------------------------------------
    # O admin real fica em DJANGO_ADMIN_URL (ex.: /painel-interno/).
    path(settings.DJANGO_ADMIN_URL, admin.site.urls),
    # --- Documentação OpenAPI ----------------------------------------------
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # --- Autenticação (JWT) -------------------------------------------------
    path("api/auth/", include("apps.authentication.urls")),
    # --- Usuários (perfil + gestão) -----------------------------------------
    path("api/", include("apps.users.urls")),
    # --- Itens (achados, perdidos e fotos) ----------------------------------
    path("api/items/", include("apps.items.urls")),
    # --- Operações (pontos, custódia, claims e retirada) --------------------
    path("api/operations/", include("apps.operations.urls")),
    # --- Auditoria (histórico + consulta administrativa) --------------------
    path("api/", include("apps.audit.urls")),
    # --- Notificações (inscrições de push) ----------------------------------
    path("api/notifications/", include("apps.notifications.urls")),
]

# Servir arquivos de mídia em desenvolvimento.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
