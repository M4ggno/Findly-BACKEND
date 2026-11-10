"""Máquina de estados do item encontrado.

As views **nunca** alteram ``status`` diretamente: toda transição passa por
``transition_found_item``, que valida o fluxo definido no README:

.. code-block:: text

    REPORTADO -> EM_CUSTODIA -> AGUARDANDO_RETIRADA -> DEVOLVIDO
         |            |
         +------------+--> EXPIRADO / ENCAMINHADO

Estados finais (``DEVOLVIDO``, ``EXPIRADO`` e ``ENCAMINHADO``) não aceitam novas
transições.
"""

from __future__ import annotations

from django.db import transaction

from apps.users.models import User

from .models import FoundItem, ItemStatus

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    ItemStatus.REPORTADO: frozenset(
        {
            ItemStatus.EM_CUSTODIA,
            ItemStatus.EXPIRADO,
            ItemStatus.ENCAMINHADO,
        }
    ),
    ItemStatus.EM_CUSTODIA: frozenset(
        {
            ItemStatus.AGUARDANDO_RETIRADA,
            ItemStatus.EXPIRADO,
            ItemStatus.ENCAMINHADO,
        }
    ),
    ItemStatus.AGUARDANDO_RETIRADA: frozenset(
        {
            ItemStatus.DEVOLVIDO,
            ItemStatus.EXPIRADO,
            ItemStatus.ENCAMINHADO,
        }
    ),
    ItemStatus.DEVOLVIDO: frozenset(),
    ItemStatus.EXPIRADO: frozenset(),
    ItemStatus.ENCAMINHADO: frozenset(),
}


class InvalidStatusTransition(ValueError):
    """Transição não permitida pela máquina de estados."""

    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Não é possível mudar o status de {current} para {target}.")


def allowed_next_statuses(current: str) -> frozenset[str]:
    """Estados alcançáveis a partir de ``current`` (usado em documentação/testes)."""
    return ALLOWED_TRANSITIONS.get(current, frozenset())


@transaction.atomic
def transition_found_item(
    item: FoundItem,
    target_status: str,
    *,
    user: User | None = None,
) -> FoundItem:
    """Valida e aplica uma transição de status de forma atômica.

    ``user`` fica registrado na assinatura porque a próxima etapa (app de
    auditoria) grava o responsável pela mudança no mesmo bloco transacional.
    """
    if target_status == item.status:
        raise InvalidStatusTransition(item.status, target_status)

    if target_status not in ALLOWED_TRANSITIONS.get(item.status, frozenset()):
        raise InvalidStatusTransition(item.status, target_status)

    previous_status = item.status
    item.status = target_status
    item.save(update_fields=["status", "updated_at"])

    # Import local evita carregar o app de auditoria durante o boot e mantém a
    # dependência em uma única direção (audit -> items no modelo).
    from apps.audit.models import AuditAction
    from apps.audit.services import record_event

    record_event(
        item=item,
        action=AuditAction.STATUS_CHANGED,
        user=user,
        previous_status=previous_status,
        new_status=target_status,
    )
    return item
