"""Views do app de itens.

Rotas montadas em ``/api/items/`` (ver ``urls.py``):

- ``GET/POST /api/items/found/`` — listagem e cadastro de achados.
- ``GET/PATCH /api/items/found/{public_code}/`` — detalhe/edição.
- ``POST /api/items/found/{public_code}/status/`` — transição de status.
- ``POST /api/items/found/{public_code}/photos/`` — upload de foto.
- ``DELETE /api/items/found/{public_code}/photos/{photo_id}/`` — remover foto.
- ``GET/POST /api/items/lost/`` — alertas de perda.
- ``GET/PATCH /api/items/lost/{public_code}/`` — detalhe/edição.
- ``POST /api/items/lost/{public_code}/cancel/`` — cancelar alerta.
"""

from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.permissions import IsOperatorOrAdmin
from services import notification_service

from .filters import FoundItemFilter, LostReportFilter
from .models import FoundItem, ItemPhoto, LostReport, LostReportStatus
from .permissions import (
    CanEditLostReport,
    CanManageItemPhotos,
    IsReporterOrOperatorOrAdmin,
)
from .serializers import (
    FoundItemSerializer,
    FoundItemStatusSerializer,
    FoundItemWriteSerializer,
    ItemPhotoSerializer,
    ItemPhotoUploadSerializer,
    LostReportSerializer,
    LostReportWriteSerializer,
)
from .services import InvalidStatusTransition, transition_found_item


@extend_schema_view(
    list=extend_schema(
        tags=["items"],
        summary="Listar itens encontrados",
        responses={200: FoundItemSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["items"],
        summary="Detalhar um item encontrado",
        responses={200: FoundItemSerializer},
    ),
    create=extend_schema(
        tags=["items"],
        summary="Cadastrar item encontrado",
        request=FoundItemWriteSerializer,
        responses={201: FoundItemSerializer},
    ),
    update=extend_schema(
        tags=["items"],
        summary="Editar item encontrado",
        request=FoundItemWriteSerializer,
        responses={200: FoundItemSerializer},
    ),
    partial_update=extend_schema(
        tags=["items"],
        summary="Editar parcialmente item encontrado",
        request=FoundItemWriteSerializer,
        responses={200: FoundItemSerializer},
    ),
)
class FoundItemViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Achados: cadastro pelo autor, edição e ciclo de vida.

    O autor edita o próprio item apenas enquanto ``REPORTADO``. Operadores e
    administradores podem editar e mudar o status. Não há exclusão: o ciclo de
    vida termina em ``DEVOLVIDO``, ``EXPIRADO`` ou ``ENCAMINHADO``.
    """

    queryset = FoundItem.objects.select_related("reported_by").prefetch_related(
        "photos"
    )
    lookup_field = "public_code"
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = FoundItemFilter
    search_fields = ["title", "description", "found_location", "public_code"]
    ordering_fields = ["created_at", "found_at", "title", "status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return FoundItemWriteSerializer
        if self.action == "change_status":
            return FoundItemStatusSerializer
        if self.action == "upload_photo":
            return ItemPhotoUploadSerializer
        return FoundItemSerializer

    def get_permissions(self):
        if self.action in {"update", "partial_update"}:
            return [IsAuthenticated(), IsReporterOrOperatorOrAdmin()]
        if self.action == "change_status":
            return [IsOperatorOrAdmin()]
        if self.action in {"upload_photo", "delete_photo"}:
            return [IsAuthenticated(), CanManageItemPhotos()]
        return [IsAuthenticated()]

    @transaction.atomic
    def perform_create(self, serializer):
        item = serializer.save(reported_by=self.request.user)

        from apps.audit.models import AuditAction
        from apps.audit.services import record_event
        from apps.operations.services import open_initial_custody

        record_event(
            item=item,
            action=AuditAction.CREATED,
            user=self.request.user,
            new_status=item.status,
        )
        # A posse física começa com quem cadastrou o achado; o evento CREATED já
        # cobre a criação (não geramos um segundo evento de custódia).
        open_initial_custody(item, self.request.user)

        # Avisa donos de alertas de perda compatíveis (agendado pós-commit).
        notification_service.notify_found_item_matches(item)

    @extend_schema(
        tags=["items"],
        summary="Mudar o status do item",
        request=FoundItemStatusSerializer,
        responses={200: FoundItemSerializer},
    )
    @action(detail=True, methods=["post"], url_path="status")
    def change_status(self, request, public_code=None):
        """Aplica uma transição válida da máquina de estados."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        item = self.get_object()
        try:
            item = transition_found_item(
                item,
                serializer.validated_data["status"],
                user=request.user,
            )
        except InvalidStatusTransition as exc:
            raise ValidationError({"status": [str(exc)]}) from exc

        return Response(
            FoundItemSerializer(item, context=self.get_serializer_context()).data
        )

    @extend_schema(
        tags=["items"],
        summary="Enviar foto do item",
        request=ItemPhotoUploadSerializer,
        responses={201: ItemPhotoSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="photos",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_photo(self, request, public_code=None):
        """Recebe uma imagem, remove EXIF e salva a versão comprimida."""
        item = self.get_object()
        serializer = self.get_serializer(
            data=request.data,
            context={**self.get_serializer_context(), "item": item},
        )
        serializer.is_valid(raise_exception=True)
        photo = serializer.save()
        return Response(
            ItemPhotoSerializer(photo, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=["items"],
        summary="Remover foto do item",
        responses={204: None},
    )
    @action(
        detail=True,
        methods=["delete"],
        url_path=r"photos/(?P<photo_id>[0-9]+)",
    )
    def delete_photo(self, request, public_code=None, photo_id=None):
        """Remove a foto do banco e do armazenamento."""
        item = self.get_object()
        photo = get_object_or_404(ItemPhoto, pk=photo_id, item=item)
        photo.image.delete(save=False)
        photo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(
        tags=["items"],
        summary="Listar itens perdidos",
        responses={200: LostReportSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["items"],
        summary="Detalhar um item perdido",
        responses={200: LostReportSerializer},
    ),
    create=extend_schema(
        tags=["items"],
        summary="Registrar item perdido",
        request=LostReportWriteSerializer,
        responses={201: LostReportSerializer},
    ),
    update=extend_schema(
        tags=["items"],
        summary="Editar item perdido",
        request=LostReportWriteSerializer,
        responses={200: LostReportSerializer},
    ),
    partial_update=extend_schema(
        tags=["items"],
        summary="Editar parcialmente item perdido",
        request=LostReportWriteSerializer,
        responses={200: LostReportSerializer},
    ),
)
class LostReportViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Alertas de perda: o dono cria e mantém o alerta enquanto aberto."""

    queryset = LostReport.objects.select_related("owner")
    lookup_field = "public_code"
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = LostReportFilter
    search_fields = ["title", "description", "lost_location", "public_code"]
    ordering_fields = ["created_at", "lost_at", "title", "status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return LostReportWriteSerializer
        return LostReportSerializer

    def get_permissions(self):
        if self.action in {"update", "partial_update", "cancel"}:
            return [IsAuthenticated(), CanEditLostReport()]
        return [IsAuthenticated()]

    @transaction.atomic
    def perform_create(self, serializer):
        report = serializer.save(owner=self.request.user)
        # Avisa o dono do alerta se já existirem achados compatíveis.
        notification_service.notify_lost_report_matches(report)

    @extend_schema(
        tags=["items"],
        summary="Cancelar alerta de perda",
        request=None,
        responses={200: LostReportSerializer},
    )
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, public_code=None):
        """Marca o alerta como ``CANCELADO`` (ação do dono/admin)."""
        report = self.get_object()
        if report.status != LostReportStatus.ABERTO:
            raise ValidationError(
                {"status": ["Apenas alertas abertos podem ser cancelados."]}
            )
        report.status = LostReportStatus.CANCELADO
        report.save(update_fields=["status", "updated_at"])
        return Response(
            LostReportSerializer(report, context=self.get_serializer_context()).data
        )
