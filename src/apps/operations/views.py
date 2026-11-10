"""Views do app de operações.

Rotas montadas em ``/api/operations/`` (ver ``urls.py``):

- ``GET/POST/PUT/PATCH /api/operations/points/`` — pontos de coleta.
- ``GET /api/operations/items/found/{code}/custody/`` — histórico de custódia.
- ``POST /api/operations/items/found/{code}/custody/transfer/`` — transferência.
- ``GET/POST /api/operations/items/found/{code}/claims/`` — claims do item.
- ``GET /api/operations/items/found/{code}/label/`` — etiqueta QR do item.
- ``GET /api/operations/claims/`` e ``.../{id}/`` — consulta de claims.
- ``POST /api/operations/claims/{id}/approve|reject|cancel/`` — decisões.
- ``POST /api/operations/withdrawals/confirm/`` — confirma retirada pelo QR.
"""

from __future__ import annotations

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.items.models import FoundItem
from apps.items.serializers import FoundItemSerializer
from apps.users.permissions import IsAdminRole, IsOperatorOrAdmin
from services.qrcode_service import build_qr_png, item_label_payload

from .filters import ClaimFilter, CollectionPointFilter
from .models import Claim, ClaimStatus, CollectionPoint, CustodyRecord
from .permissions import CanViewClaim, CanViewCustody, IsClaimantOrAdmin
from .serializers import (
    ClaimCreateSerializer,
    ClaimDecisionSerializer,
    ClaimSerializer,
    CollectionPointSerializer,
    CustodyRecordSerializer,
    CustodyTransferSerializer,
    WithdrawalConfirmSerializer,
)
from .services import (
    InvalidClaim,
    InvalidCustody,
    InvalidWithdrawal,
    approve_claim,
    cancel_claim,
    confirm_withdrawal,
    reject_claim,
    submit_claim,
    transfer_to_point,
)


def _validation_error(exc: Exception) -> ValidationError:
    return ValidationError({"detail": str(exc)})


@extend_schema_view(
    list=extend_schema(
        tags=["operations"],
        summary="Listar pontos de coleta",
        responses={200: CollectionPointSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["operations"],
        summary="Detalhar ponto de coleta",
        responses={200: CollectionPointSerializer},
    ),
    create=extend_schema(
        tags=["operations"],
        summary="Criar ponto de coleta (admin)",
        request=CollectionPointSerializer,
        responses={201: CollectionPointSerializer},
    ),
    update=extend_schema(
        tags=["operations"],
        summary="Editar ponto de coleta (admin)",
        request=CollectionPointSerializer,
        responses={200: CollectionPointSerializer},
    ),
    partial_update=extend_schema(
        tags=["operations"],
        summary="Editar parcialmente ponto de coleta (admin)",
        request=CollectionPointSerializer,
        responses={200: CollectionPointSerializer},
    ),
)
class CollectionPointViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Pontos de coleta: leitura autenticada, escrita apenas admin."""

    queryset = CollectionPoint.objects.prefetch_related("operators")
    serializer_class = CollectionPointSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CollectionPointFilter
    search_fields = ["name", "address"]
    ordering_fields = ["name", "created_at", "capacity"]
    ordering = ["name"]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update"}:
            return [IsAdminRole()]
        return [IsAuthenticated()]


class ItemCustodyView(generics.ListAPIView):
    """Histórico de custódia de um item (autor, operador ou admin)."""

    serializer_class = CustodyRecordSerializer
    permission_classes = [IsAuthenticated, CanViewCustody]
    pagination_class = None
    filter_backends: list = []

    def get_queryset(self):
        item = get_object_or_404(
            FoundItem.objects.select_related("reported_by"),
            public_code=self.kwargs["public_code"],
        )
        self.check_object_permissions(self.request, item)
        return CustodyRecord.objects.filter(item=item).select_related(
            "item", "held_by_user", "collection_point"
        )


class CustodyTransferView(APIView):
    """Transfere a custódia do item para um ponto de coleta."""

    permission_classes = [IsOperatorOrAdmin]

    @extend_schema(
        tags=["operations"],
        summary="Transferir custódia para um ponto de coleta",
        request=CustodyTransferSerializer,
        responses={201: CustodyRecordSerializer},
    )
    def post(self, request, public_code: str):
        item = get_object_or_404(FoundItem, public_code=public_code)
        serializer = CustodyTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            record = transfer_to_point(
                item,
                serializer.validated_data["collection_point"],
                user=request.user,
                note=serializer.validated_data.get("note", ""),
            )
        except InvalidCustody as exc:
            raise _validation_error(exc) from exc

        return Response(
            CustodyRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )


class ItemClaimListCreateView(generics.ListCreateAPIView):
    """Lista (próprios) claims do item e permite abrir um novo."""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ClaimCreateSerializer
        return ClaimSerializer

    def _item(self) -> FoundItem:
        return get_object_or_404(FoundItem, public_code=self.kwargs["public_code"])

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Claim.objects.none()
        item = self._item()
        queryset = Claim.objects.filter(item=item).select_related(
            "item", "claimant", "reviewed_by"
        )
        user = self.request.user
        if not (user.is_admin or user.is_operator):
            queryset = queryset.filter(claimant=user)
        return queryset

    @extend_schema(
        tags=["operations"],
        summary="Listar reivindicações do item",
        responses={200: ClaimSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["operations"],
        summary="Abrir reivindicação do item",
        request=ClaimCreateSerializer,
        responses={201: ClaimSerializer},
    )
    def post(self, request, *args, **kwargs):
        item = self._item()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            claim = submit_claim(
                item,
                request.user,
                message=serializer.validated_data.get("message", ""),
            )
        except InvalidClaim as exc:
            raise _validation_error(exc) from exc

        return Response(
            ClaimSerializer(claim, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    list=extend_schema(
        tags=["operations"],
        summary="Listar reivindicações",
        responses={200: ClaimSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["operations"],
        summary="Detalhar reivindicação",
        responses={200: ClaimSerializer},
    ),
)
class ClaimViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Consulta e decisão de claims (aprovar, recusar, cancelar)."""

    queryset = Claim.objects.select_related(
        "item", "claimant", "reviewed_by"
    ).select_related("withdrawal")
    serializer_class = ClaimSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ClaimFilter
    search_fields = ["item__public_code", "item__title", "claimant__full_name"]
    ordering_fields = ["created_at", "status"]
    ordering = ["-created_at", "-id"]

    def get_permissions(self):
        if self.action in {"approve", "reject"}:
            return [IsOperatorOrAdmin()]
        if self.action == "cancel":
            return [IsAuthenticated(), IsClaimantOrAdmin()]
        if self.action == "retrieve":
            return [IsAuthenticated(), CanViewClaim()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        # ``retrieve``/``cancel`` precisam enxergar o registro para que a
        # permissão de objeto devolva 403 (em vez de 404) a quem não é o autor.
        if self.action in {"retrieve", "cancel"}:
            return queryset
        if user.is_admin or user.is_operator:
            return queryset
        return queryset.filter(claimant=user)

    def get_serializer_class(self):
        if self.action in {"approve", "reject"}:
            return ClaimDecisionSerializer
        return ClaimSerializer

    @extend_schema(
        tags=["operations"],
        summary="Aprovar reivindicação",
        request=ClaimDecisionSerializer,
        responses={200: ClaimSerializer},
    )
    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            claim = approve_claim(
                self.get_object(),
                user=request.user,
                decision_note=serializer.validated_data.get("decision_note", ""),
            )
        except InvalidClaim as exc:
            raise _validation_error(exc) from exc

        return Response(ClaimSerializer(claim, context={"request": request}).data)

    @extend_schema(
        tags=["operations"],
        summary="Recusar reivindicação",
        request=ClaimDecisionSerializer,
        responses={200: ClaimSerializer},
    )
    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            claim = reject_claim(
                self.get_object(),
                user=request.user,
                decision_note=serializer.validated_data.get("decision_note", ""),
            )
        except InvalidClaim as exc:
            raise _validation_error(exc) from exc

        return Response(ClaimSerializer(claim, context={"request": request}).data)

    @extend_schema(
        tags=["operations"],
        summary="Cancelar reivindicação",
        request=None,
        responses={200: ClaimSerializer},
    )
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        try:
            claim = cancel_claim(self.get_object(), user=request.user)
        except InvalidClaim as exc:
            raise _validation_error(exc) from exc

        return Response(ClaimSerializer(claim, context={"request": request}).data)


class WithdrawalConfirmView(APIView):
    """Confirma a retirada a partir do token lido do QR Code."""

    permission_classes = [IsOperatorOrAdmin]

    @extend_schema(
        tags=["operations"],
        summary="Confirmar retirada via QR Code",
        request=WithdrawalConfirmSerializer,
        responses={200: ClaimSerializer},
    )
    def post(self, request):
        serializer = WithdrawalConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            authority = confirm_withdrawal(
                serializer.validated_data["token"], user=request.user
            )
        except InvalidWithdrawal as exc:
            raise _validation_error(exc) from exc

        claim = Claim.objects.select_related("item", "claimant", "reviewed_by").get(
            pk=authority.claim_id
        )
        item = FoundItem.objects.get(pk=claim.item_id)

        return Response(
            {
                "detail": "Retirada confirmada.",
                "item": FoundItemSerializer(item).data,
                "claim": ClaimSerializer(claim, context={"request": request}).data,
            }
        )


class ItemLabelView(APIView):
    """Devolve a etiqueta QR de identificação do item (PNG)."""

    permission_classes = [IsAuthenticated, CanViewCustody]

    @extend_schema(
        tags=["operations"],
        summary="Gerar etiqueta QR do item",
        responses={(200, "image/png"): bytes},
    )
    def get(self, request, public_code: str):
        item = get_object_or_404(
            FoundItem.objects.select_related("reported_by"),
            public_code=public_code,
        )
        self.check_object_permissions(request, item)

        content = build_qr_png(item_label_payload(item))
        response = HttpResponse(content.read(), content_type="image/png")
        response["Content-Disposition"] = (
            f'inline; filename="findly-{item.public_code}.png"'
        )
        return response


__all__ = [
    "ClaimStatus",
    "ClaimViewSet",
    "CollectionPointViewSet",
    "CustodyTransferView",
    "ItemClaimListCreateView",
    "ItemCustodyView",
    "ItemLabelView",
    "WithdrawalConfirmView",
]
