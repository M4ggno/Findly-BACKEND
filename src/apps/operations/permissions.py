"""Permissões do app de operações."""

from __future__ import annotations

from rest_framework.permissions import BasePermission


class CanViewCustody(BasePermission):
    """Histórico de custódia: autor do item, operador ou administrador."""

    message = "Apenas o autor, operadores ou administradores podem ver a custódia."

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.is_admin or user.is_operator or obj.reported_by_id == user.pk


class CanViewClaim(BasePermission):
    """Detalhe do claim: autor do claim, operador ou administrador."""

    message = "Apenas o autor da reivindicação, operadores ou administradores."

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.is_admin or user.is_operator or obj.claimant_id == user.pk


class IsClaimantOrAdmin(BasePermission):
    """Cancelamento: apenas quem abriu o claim (ou administrador)."""

    message = "Apenas o autor da reivindicação pode cancelá-la."

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.is_admin or obj.claimant_id == user.pk
