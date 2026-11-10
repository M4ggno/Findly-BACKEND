"""Regras de negócio da auditoria.

A gravação é feita **dentro da transação** da operação que a originou. Se o
evento falhar, a operação inteira é revertida (README, seção 3.5).
"""

from __future__ import annotations

from typing import Any

from apps.items.models import FoundItem
from apps.users.models import User

from .models import AuditAction, AuditEvent


def record_event(
    *,
    item: FoundItem,
    action: str,
    user: User | None = None,
    previous_status: str = "",
    new_status: str = "",
    collection_point=None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Cria um evento imutável de auditoria."""
    return AuditEvent.objects.create(
        item=item,
        action=action,
        responsible=user,
        previous_status=previous_status,
        new_status=new_status,
        collection_point=collection_point,
        metadata=metadata or {},
    )


__all__ = ["AuditAction", "AuditEvent", "record_event"]
