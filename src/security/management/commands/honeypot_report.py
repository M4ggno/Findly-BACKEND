"""Management command para inspecionar/gerenciar o honeypot.

Uso::

    python manage.py honeypot_report                # últimos 50 eventos + blocklist
    python manage.py honeypot_report --limit 200    # mais eventos
    python manage.py honeypot_report --clear        # limpa o histórico
    python manage.py honeypot_report --unblock 1.2.3.4
    python manage.py honeypot_report --unblock-all
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from security import honeypot


class Command(BaseCommand):
    help = "Exibe/gerencia os eventos capturados pelo honeypot de segurança."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=50, help="Nº de eventos recentes a exibir."
        )
        parser.add_argument(
            "--clear", action="store_true", help="Limpa o histórico de eventos."
        )
        parser.add_argument(
            "--unblock", metavar="IP", help="Remove um IP específico da blocklist."
        )
        parser.add_argument(
            "--unblock-all", action="store_true", help="Esvazia toda a blocklist."
        )

    def handle(self, *args, **options):
        if options["clear"]:
            honeypot.clear_events()
            self.stdout.write(self.style.SUCCESS("Histórico de eventos limpo."))
            return

        if options["unblock"]:
            ip = options["unblock"]
            if honeypot.unblock_ip(ip):
                self.stdout.write(self.style.SUCCESS(f"IP {ip} removido da blocklist."))
            else:
                self.stdout.write(self.style.WARNING(f"IP {ip} não estava bloqueado."))
            return

        if options["unblock_all"]:
            ips = honeypot.blocked_ips()
            for ip in ips:
                honeypot.unblock_ip(ip)
            self.stdout.write(
                self.style.SUCCESS(f"Blocklist esvaziada ({len(ips)} IPs).")
            )
            return

        blocked = honeypot.blocked_ips()
        events = honeypot.recent_events(limit=options["limit"])

        self.stdout.write(
            self.style.MIGRATE_HEADING(f"IPs bloqueados ({len(blocked)}):")
        )
        for ip in blocked or ["(nenhum)"]:
            self.stdout.write(f"  - {ip}")

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(f"Eventos recentes ({len(events)}):")
        )
        for event in events:
            self.stdout.write(
                f"  [{event.get('timestamp')}] {event.get('kind')} "
                f"ip={event.get('ip')} {event.get('method')} "
                f"{event.get('path')} hits={event.get('hits', '-')}"
            )
            if event.get("attempted_username"):
                self.stdout.write(
                    f"      usuario={event['attempted_username']!r} "
                    f"senha_len={event.get('password_length')} "
                    f"sha256={str(event.get('password_sha256'))[:16]}..."
                )
        if not events:
            self.stdout.write("  (nenhum)")
