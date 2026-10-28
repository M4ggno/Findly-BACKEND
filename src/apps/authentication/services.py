"""Regras de negócio da autenticação (mantidas fora das views)."""

from __future__ import annotations

import logging

from apps.users.models import User

logger = logging.getLogger("findly.authentication")


def blacklist_user_tokens(user: User) -> int:
    """Invalida todos os *refresh tokens* emitidos para o usuário.

    Chamado após a redefinição de senha: sessões antigas deixam de conseguir
    renovar o *access token*. Retorna quantos tokens foram invalidados agora.

    A importação é local para não carregar os modelos do app de blacklist
    durante a inicialização do Django.
    """
    from rest_framework_simplejwt.token_blacklist.models import (
        BlacklistedToken,
        OutstandingToken,
    )

    revoked = 0
    for token in OutstandingToken.objects.filter(user=user).iterator():
        _, created = BlacklistedToken.objects.get_or_create(token=token)
        if created:
            revoked += 1
    return revoked
