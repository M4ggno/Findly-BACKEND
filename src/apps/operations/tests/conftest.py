"""Fixtures dos testes do app de operações."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

PASSWORD = "S3nh@Forte!2026"


@pytest.fixture(autouse=True)
def _hermetic_settings(settings, tmp_path):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def common_user(db):
    from apps.users.models import User

    return User.objects.create_user(
        email="comum@findly.local",
        password=PASSWORD,
        full_name="Usuário Comum",
    )


@pytest.fixture
def other_user(db):
    from apps.users.models import User

    return User.objects.create_user(
        email="outro@findly.local",
        password=PASSWORD,
        full_name="Outro Usuário",
    )


@pytest.fixture
def operator_user(db):
    from apps.users.models import User

    return User.objects.create_user(
        email="operador@findly.local",
        password=PASSWORD,
        full_name="Operador de Ponto",
        role="operator",
    )


@pytest.fixture
def admin_user(db):
    from apps.users.models import User

    return User.objects.create_user(
        email="admin@findly.local",
        password=PASSWORD,
        full_name="Administrador",
        role="admin",
        is_staff=True,
    )


def _client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def auth_client(common_user) -> APIClient:
    return _client_for(common_user)


@pytest.fixture
def other_client(other_user) -> APIClient:
    return _client_for(other_user)


@pytest.fixture
def operator_client(operator_user) -> APIClient:
    return _client_for(operator_user)


@pytest.fixture
def admin_client(admin_user) -> APIClient:
    return _client_for(admin_user)


@pytest.fixture
def found_item(db, common_user):
    from apps.items.models import Category, FoundItem

    return FoundItem.objects.create(
        reported_by=common_user,
        title="Carteira preta",
        description="Carteira de couro com documentos.",
        category=Category.CARTEIRAS,
        found_at=timezone.now() - timedelta(days=1),
        found_location="Recepção do prédio A",
    )


@pytest.fixture
def point(db, operator_user):
    from apps.operations.models import CollectionPoint

    point = CollectionPoint.objects.create(
        name="Recepção Central",
        address="Rua A, 100",
        opening_hours="Seg a Sex, 08:00-18:00",
        capacity=5,
    )
    point.operators.add(operator_user)
    return point


@pytest.fixture
def other_point(db, operator_user):
    from apps.operations.models import CollectionPoint

    point = CollectionPoint.objects.create(
        name="Guarita do estacionamento",
        address="Rua B, 200",
        capacity=None,
    )
    point.operators.add(operator_user)
    return point


@pytest.fixture
def item_in_custody(db, found_item, point):
    from apps.items.models import ItemStatus
    from apps.operations.models import CustodyRecord

    found_item.status = ItemStatus.EM_CUSTODIA
    found_item.save(update_fields=["status"])
    CustodyRecord.objects.create(item=found_item, collection_point=point)
    return found_item


@pytest.fixture
def pending_claim(db, item_in_custody, other_user):
    from apps.operations.models import Claim

    return Claim.objects.create(
        item=item_in_custody,
        claimant=other_user,
        message="Tenho a nota fiscal e fotos da carteira.",
    )


@pytest.fixture
def found_payload():
    return {
        "title": "Mochila azul",
        "description": "Mochila com notebook e caderno.",
        "category": "eletronicos",
        "found_at": (timezone.now() - timedelta(hours=2)).isoformat(),
        "found_location": "Biblioteca central",
    }


@pytest.fixture
def approved_claim(pending_claim, operator_user):
    from apps.operations.services import approve_claim

    return approve_claim(pending_claim, user=operator_user)
