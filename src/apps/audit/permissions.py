"""Permissões do app de auditoria."""

from __future__ import annotations

from rest_framework.permissions import BasePermission


class CanViewItemHistory(BasePermission):
    """Histórico de um item: autor, operador ou administrador."""

    message = "Apenas o autor, operadores ou administradores podem ver o histórico."

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.is_admin or user.is_operator or obj.reported_by_id == user.pk
