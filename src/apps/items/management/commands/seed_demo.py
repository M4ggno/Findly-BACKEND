"""Popula o banco com dados de demonstração (idempotente).

O objetivo é deixar o front com um ambiente pronto para explorar os fluxos:
usuários de cada papel, pontos de coleta, achados em estados diferentes, um
claim aprovado com QR de retirada e alertas de perda (incluindo um match).

Uso::

    python manage.py seed_demo
    python manage.py seed_demo --reset-passwords
    python manage.py seed_demo --force --password 'OutraSenha!2026'

O comando pode rodar quantas vezes for preciso: usuários são buscados por
e-mail, itens/pontos por nome/código e claims pelo item. Dados já existentes
**não** são apagados nem têm o status resetado.

Segurança: por padrão só roda com ``DEBUG=True``; em produção é preciso
``--force`` (as senhas demo são conhecidas).
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test.utils import override_settings
from django.utils import timezone

from apps.audit.models import AuditAction
from apps.audit.services import record_event
from apps.items.models import (
    Category,
    FoundItem,
    ItemStatus,
    LostReport,
    LostReportStatus,
)
from apps.operations.models import Claim, ClaimStatus, CollectionPoint
from apps.operations.services import (
    approve_claim,
    current_collection_point,
    open_initial_custody,
    submit_claim,
    transfer_to_point,
)
from apps.users.models import Role, User

DEMO_PASSWORD = "Findly@2026!"

# Códigos fixos (10 caracteres do alfabeto público) para o seed ser idempotente.
FOUND_WALLET = "DEMOACHADO"
FOUND_KEYS = "DEMOCHAVES"
FOUND_LAPTOP = "DEMOCARTEI"
LOST_WALLET = "DEMOPERDID"
LOST_UMBRELLA = "DEMOALERTA"


class Command(BaseCommand):
    help = "Cria dados de demonstração idempotentes para o front-end."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=DEMO_PASSWORD,
            help="Senha das contas demo (padrão: %(default)s).",
        )
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Redefine a senha das contas demo mesmo que já existam.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Permite rodar com DEBUG=False (produção).",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "seed_demo cria contas com senha conhecida. Use --force se "
                "realmente quiser popular este ambiente."
            )

        password = options["password"]
        reset = options["reset_passwords"]

        # Silencia e-mail/push: o seed cria custódias e claims, que disparam
        # notificações via on_commit.
        quiet = {
            "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
            "NOTIFICATIONS_PUSH_ENABLED": False,
            "NOTIFICATIONS_ASYNC_ENABLED": False,
        }

        with override_settings(**quiet):
            with transaction.atomic():
                stats = self._seed(password, reset)

        self._report(stats, password)

    # ------------------------------------------------------------------
    # Seed
    # ------------------------------------------------------------------
    def _seed(self, password: str, reset: bool) -> dict[str, int]:
        stats = {
            "users": 0,
            "points": 0,
            "items": 0,
            "lost_reports": 0,
            "claims": 0,
            "transfers": 0,
        }

        demo = self._user(
            "demo@findly.local",
            "Usuária Demo",
            Role.COMMON,
            password,
            reset,
            stats,
        )
        claimant = self._user(
            "reivindicante@findly.local",
            "Reivindicante Demo",
            Role.COMMON,
            password,
            reset,
            stats,
        )
        operator = self._user(
            "operador@findly.local",
            "Operador Demo",
            Role.OPERATOR,
            password,
            reset,
            stats,
        )
        self._user(
            "admin@findly.local",
            "Administrador Demo",
            Role.ADMIN,
            password,
            reset,
            stats,
            admin=True,
        )

        point_a = self._point(
            "Portaria do Prédio A",
            "Av. Central, 100 — térreo",
            "Seg a Sex, 08:00–18:00",
            capacity=50,
            operator=operator,
            stats=stats,
        )
        self._point(
            "Biblioteca Central",
            "Av. Central, 250 — 2º andar",
            "Seg a Sáb, 09:00–21:00",
            capacity=20,
            operator=operator,
            stats=stats,
        )

        now = timezone.now()

        wallet = self._found_item(
            code=FOUND_WALLET,
            reported_by=demo,
            title="Carteira de couro preta",
            description=(
                "Carteira preta com documentos, dois cartões e uma foto. "
                "Encontrada próximo à recepção."
            ),
            category=Category.CARTEIRAS,
            found_at=now - timedelta(days=2),
            found_location="Recepção do Prédio A",
            stats=stats,
        )
        if self._ensure_at_point(wallet, point_a, operator):
            stats["transfers"] += 1

        self._found_item(
            code=FOUND_KEYS,
            reported_by=operator,
            title="Chaves com chaveiro azul",
            description="Molho com três chaves e chaveiro de plástico azul.",
            category=Category.CHAVES,
            found_at=now - timedelta(days=1, hours=3),
            found_location="Biblioteca Central — mesa 12",
            stats=stats,
        )

        laptop = self._found_item(
            code=FOUND_LAPTOP,
            reported_by=operator,
            title="Notebook Dell prata",
            description=(
                "Notebook Dell Inspiron prateado com adesivo de gato na tampa. "
                "Aguardando retirada na portaria."
            ),
            category=Category.ELETRONICOS,
            found_at=now - timedelta(days=3),
            found_location="Sala 204 — bloco B",
            stats=stats,
        )
        if self._ensure_at_point(laptop, point_a, operator):
            stats["transfers"] += 1
        self._ensure_claim_approved(laptop, claimant, operator, stats)

        self._lost_report(
            code=LOST_WALLET,
            owner=demo,
            title="Carteira de couro preta",
            description="Carteira preta com documentos e cartões. Perdi na recepção.",
            category=Category.CARTEIRAS,
            lost_at=now - timedelta(days=4),
            lost_location="Recepção do Prédio A",
            read_only=stats,
        )

        self._lost_report(
            code=LOST_UMBRELLA,
            owner=claimant,
            title="Guarda-chuva azul",
            description="Guarda-chuva azul de cabo comprido, esquecido na biblioteca.",
            category=Category.OUTROS,
            lost_at=now - timedelta(days=2),
            lost_location="Biblioteca Central",
            read_only=stats,
        )

        # Evita variável não usada sem perder a legibilidade das etapas.
        return stats

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _user(
        self,
        email: str,
        full_name: str,
        role: str,
        password: str,
        reset: bool,
        stats: dict[str, int],
        *,
        admin: bool = False,
    ) -> User:
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "full_name": full_name,
                "role": role,
                "is_active": True,
            },
        )
        if created:
            stats["users"] += 1

        changed: list[str] = []
        if created or reset:
            user.set_password(password)
            changed.append("password")
        if user.full_name != full_name:
            user.full_name = full_name
            changed.append("full_name")
        if user.role != role:
            user.role = role
            changed.append("role")
        if admin and not (user.is_staff and user.is_superuser):
            user.is_staff = True
            user.is_superuser = True
            changed.extend(["is_staff", "is_superuser"])

        if changed:
            user.save(update_fields=list(dict.fromkeys(changed)))
        return user

    def _point(
        self,
        name: str,
        address: str,
        opening_hours: str,
        *,
        capacity: int,
        operator: User,
        stats: dict[str, int],
    ) -> CollectionPoint:
        point, created = CollectionPoint.objects.get_or_create(
            name=name,
            defaults={
                "address": address,
                "opening_hours": opening_hours,
                "capacity": capacity,
                "is_active": True,
            },
        )
        if created:
            stats["points"] += 1
        if not point.operators.filter(pk=operator.pk).exists():
            point.operators.add(operator)
        return point

    def _found_item(
        self,
        *,
        code: str,
        reported_by: User,
        title: str,
        description: str,
        category: str,
        found_at,
        found_location: str,
        stats: dict[str, int],
    ) -> FoundItem:
        item, created = FoundItem.objects.get_or_create(
            public_code=code,
            defaults={
                "reported_by": reported_by,
                "title": title,
                "description": description,
                "category": category,
                "found_at": found_at,
                "found_location": found_location,
            },
        )
        if not created:
            return item

        stats["items"] += 1
        record_event(
            item=item,
            action=AuditAction.CREATED,
            user=reported_by,
            new_status=item.status,
        )
        open_initial_custody(item, reported_by, note="Cadastro do item (seed demo)")
        return item

    def _ensure_at_point(
        self, item: FoundItem, point: CollectionPoint, operator: User
    ) -> bool:
        item = FoundItem.objects.get(pk=item.pk)
        if item.is_terminal:
            return False
        if current_collection_point(item) == point:
            return False
        transfer_to_point(item, point, user=operator, note="Transferência (seed demo)")
        return True

    def _ensure_claim_approved(
        self,
        item: FoundItem,
        claimant: User,
        reviewer: User,
        stats: dict[str, int],
    ) -> bool:
        # A transferência acima mudou o status no banco; relê antes de decidir.
        item = FoundItem.objects.get(pk=item.pk)
        if item.is_terminal:
            return False
        if Claim.objects.filter(item=item, status=ClaimStatus.APPROVED).exists():
            return False
        if item.status not in {ItemStatus.EM_CUSTODIA, ItemStatus.AGUARDANDO_RETIRADA}:
            return False

        claim = Claim.objects.filter(
            item=item, claimant=claimant, status=ClaimStatus.PENDING
        ).first()
        created = False
        if claim is None:
            claim = submit_claim(
                item,
                claimant,
                message="É meu notebook; tenho a nota fiscal e o número de série.",
            )
            created = True
            stats["claims"] += 1

        approve_claim(
            claim,
            user=reviewer,
            decision_note="Documentação conferida na portaria (seed demo).",
        )
        return created

    def _lost_report(
        self,
        *,
        code: str,
        owner: User,
        title: str,
        description: str,
        category: str,
        lost_at,
        lost_location: str,
        read_only: dict[str, int],
    ) -> LostReport:
        report, created = LostReport.objects.get_or_create(
            public_code=code,
            defaults={
                "owner": owner,
                "title": title,
                "description": description,
                "category": category,
                "lost_at": lost_at,
                "lost_location": lost_location,
                "status": LostReportStatus.ABERTO,
            },
        )
        if created:
            read_only["lost_reports"] += 1
        return report

    # ------------------------------------------------------------------
    # Saída
    # ------------------------------------------------------------------
    def _report(self, stats: dict[str, int], password: str) -> None:
        total = sum(stats.values())
        if total == 0:
            self.stdout.write(
                self.style.WARNING(
                    "Nada a criar: os dados de demonstração já estavam completos."
                )
            )
            return

        self.stdout.write(self.style.SUCCESS("Findly — dados de demonstração"))
        self.stdout.write(
            f"  usuários.......: {stats['users']}\n"
            f"  pontos.........: {stats['points']}\n"
            f"  achados........: {stats['items']}\n"
            f"  alertas........: {stats['lost_reports']}\n"
            f"  claims.........: {stats['claims']}\n"
            f"  transferências.: {stats['transfers']}"
        )
        self.stdout.write("")
        self.stdout.write(f"Contas demo (senha: {password}):")
        self.stdout.write("  demo@findly.local          — usuário comum")
        self.stdout.write("  reivindicante@findly.local — usuário comum")
        self.stdout.write("  operador@findly.local      — operador de ponto")
        self.stdout.write("  admin@findly.local         — administrador")
        self.stdout.write("")
        self.stdout.write("Códigos para testar:")
        self.stdout.write(f"  achado em custódia....: {FOUND_WALLET}")
        self.stdout.write(f"  achado reportado......: {FOUND_KEYS}")
        self.stdout.write(f"  aguardando retirada...: {FOUND_LAPTOP}")
        self.stdout.write(f"  alerta de perda.......: {LOST_WALLET}")
        self.stdout.write(f"  alerta sem match......: {LOST_UMBRELLA}")
