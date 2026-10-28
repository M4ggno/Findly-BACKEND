"""Permissões por papel do Findly.

O modelo ``User`` tem três papéis (``common``, ``operator`` e ``admin``). As
permissões abaixo traduzem esses papéis em regras reutilizáveis pelas views.
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Permite apenas administradores (papel ``admin`` ou superusuário)."""

    message = "Apenas administradores podem acessar este recurso."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_admin)


class IsOperatorOrAdmin(BasePermission):
    """Permite operadores de ponto de coleta e administradores.

    Usada pelos apps de itens/operações, que exigem alguém responsável por um
    ponto de coleta (o usuário comum só enxerga os próprios registros).
    """

    message = "Apenas operadores ou administradores podem acessar este recurso."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user and user.is_authenticated and (user.is_operator or user.is_admin)
        )
