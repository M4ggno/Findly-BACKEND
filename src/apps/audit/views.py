"""Views da auditoria.

- ``GET /api/items/found/{public_code}/history/`` — histórico do item (autor,
  operador ou admin).
- ``GET /api/audit/`` e ``GET /api/audit/{id}/`` — consulta administrativa.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, mixins, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated

from apps.items.models import FoundItem
from apps.users.permissions import IsAdminRole

from .filters import AuditEventFilter
from .models import AuditEvent
from .permissions import CanViewItemHistory
from .serializers import AuditEventSerializer


class ItemHistoryView(generics.ListAPIView):
    """Trilha de auditoria de um item específico."""

    serializer_class = AuditEventSerializer
    permission_classes = [IsAuthenticated, CanViewItemHistory]
    pagination_class = None
    filter_backends: list = []

    def get_queryset(self):
        item = get_object_or_404(
            FoundItem.objects.select_related("reported_by"),
            public_code=self.kwargs["public_code"],
        )
        self.check_object_permissions(self.request, item)
        return AuditEvent.objects.filter(item=item).select_related("responsible")


@extend_schema_view(
    list=extend_schema(
        tags=["audit"],
        summary="Listar eventos de auditoria (administração)",
        responses={200: AuditEventSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["audit"],
        summary="Detalhar um evento de auditoria (administração)",
        responses={200: AuditEventSerializer},
    ),
)
class AuditEventViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Consulta administrativa da trilha (somente leitura)."""

    queryset = AuditEvent.objects.select_related(
        "item", "responsible", "collection_point"
    )
    serializer_class = AuditEventSerializer
    permission_classes = [IsAdminRole]
    http_method_names = ["get", "head", "options"]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = AuditEventFilter
    search_fields = [
        "item__public_code",
        "item__title",
        "responsible__full_name",
        "collection_point__name",
    ]
    ordering_fields = ["created_at", "action"]
    ordering = ["-created_at", "-id"]
