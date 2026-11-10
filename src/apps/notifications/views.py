"""Views das inscrições de push.

- ``GET/POST /api/notifications/subscriptions/`` — lista/registra as inscrições
  do próprio usuário.
- ``DELETE /api/notifications/subscriptions/{id}/`` — remove a inscrição.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, mixins
from rest_framework.permissions import IsAuthenticated

from .models import PushSubscription
from .serializers import PushSubscriptionSerializer


@extend_schema_view(
    get=extend_schema(
        tags=["notifications"],
        summary="Listar inscrições de push",
        responses={200: PushSubscriptionSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["notifications"],
        summary="Registrar inscrição de push",
        request=PushSubscriptionSerializer,
        responses={201: PushSubscriptionSerializer},
    ),
)
class PushSubscriptionListCreateView(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    generics.GenericAPIView,
):
    """Inscrições de push do usuário autenticado (sem paginação)."""

    serializer_class = PushSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    queryset = PushSubscription.objects.none()

    def get_queryset(self):
        return PushSubscription.objects.filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


@extend_schema_view(
    delete=extend_schema(
        tags=["notifications"],
        summary="Remover inscrição de push",
        responses={204: None},
    ),
)
class PushSubscriptionDetailView(mixins.DestroyModelMixin, generics.GenericAPIView):
    """Remove uma inscrição do próprio usuário (``404`` para as demais)."""

    serializer_class = PushSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    queryset = PushSubscription.objects.none()

    def get_queryset(self):
        return PushSubscription.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


__all__ = ["PushSubscriptionDetailView", "PushSubscriptionListCreateView"]
