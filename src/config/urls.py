"""Roteamento de URLs raiz do Findly Backend.

As rotas de cada app de domínio (``apps.*``) serão incluídas aqui conforme forem
implementadas (ver TODO abaixo). Por enquanto expõe o Django Admin (em caminho
secreto), o honeypot em ``/admin/`` e a documentação OpenAPI/Swagger da API.
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

urlpatterns = [
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
    #
    # --- Apps de domínio ----------------------------------------------------
    # TODO(apps): incluir as rotas de users, items, operations e audit.
]

# Servir arquivos de mídia em desenvolvimento.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
