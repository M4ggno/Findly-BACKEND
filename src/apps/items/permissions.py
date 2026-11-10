"""Permissões do app de itens.

- Qualquer usuário autenticado pode **listar/consultar** achados e perdidos.
- O autor edita o próprio registro; operadores e administradores editam qualquer
  um (correções operacionais).
- Achado só é editável pelo autor enquanto está ``REPORTADO``. Depois disso, só
  operador/admin.
- Fotos podem ser enviadas pelo autor (enquanto o item não é terminal) e por
  operador/admin.
"""

from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import ItemStatus


class IsReporterOrOperatorOrAdmin(BasePermission):
    """Edição de achados: autor enquanto reportado, ou operador/admin."""

    message = (
        "Apenas o autor pode editar o item enquanto ele está REPORTADO; "
        "depois disso, somente operadores ou administradores."
    )

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if request.method in SAFE_METHODS:
            return True
        if not user or not user.is_authenticated:
            return False
        if user.is_admin or user.is_operator:
            return True
        return obj.reported_by_id == user.pk and obj.status == ItemStatus.REPORTADO


class CanEditLostReport(BasePermission):
    """Edição de alertas de perda: dono (enquanto aberto) ou administrador."""

    message = (
        "Apenas o dono pode editar o alerta enquanto ele está ABERTO; "
        "administradores podem editar qualquer alerta."
    )

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if request.method in SAFE_METHODS:
            return True
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return True
        if getattr(view, "action", None) == "cancel":
            # O dono precisa chegar na view para receber o 400 explicativo quando
            # o alerta já não está mais ABERTO.
            return obj.owner_id == user.pk
        return obj.owner_id == user.pk and obj.status == "ABERTO"


class CanManageItemPhotos(BasePermission):
    """Upload/remoção de fotos do achado."""

    message = "Você não pode alterar as fotos deste item."

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin or user.is_operator:
            return True
        if obj.reported_by_id != user.pk:
            return False
        return not obj.is_terminal
