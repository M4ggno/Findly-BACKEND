from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


class Role(models.TextChoices):
    """Papéis de acesso no Findly (ver README, seção de Usuários)."""

    COMMON = "common", "Usuário Comum"
    OPERATOR = "operator", "Operador de Ponto de Coleta"
    ADMIN = "admin", "Administrador"


class User(AbstractBaseUser, PermissionsMixin):
    """Usuário customizado do Findly.

    Usa **e-mail** como identificador de login (não username). O modelo já é
    definido nesta etapa para travar ``AUTH_USER_MODEL`` **antes da primeira
    migração** — trocá-lo depois exigiria recriar o banco.
    """

    email = models.EmailField("e-mail", unique=True)
    full_name = models.CharField("nome completo", max_length=255, blank=True)
    phone = models.CharField("telefone", max_length=20, blank=True)

    role = models.CharField(
        "papel",
        max_length=20,
        choices=Role.choices,
        default=Role.COMMON,
    )

    is_active = models.BooleanField("ativo", default=True)
    is_staff = models.BooleanField("equipe", default=False)

    date_joined = models.DateTimeField("data de cadastro", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return self.email

    @property
    def short_name(self) -> str:
        return self.full_name.split(" ")[0] if self.full_name else self.email

    @property
    def is_operator(self) -> bool:
        return self.role == Role.OPERATOR

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN or self.is_superuser
