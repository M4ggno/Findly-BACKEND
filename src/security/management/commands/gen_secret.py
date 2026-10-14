"""Gera chaves/segredos aleatórios para o ambiente local.

Uso::

    python manage.py gen_secret
    make gen-secret
"""
from __future__ import annotations

import secrets
from pathlib import Path

from django.core.management.base import BaseCommand
from django.core.management.utils import get_random_secret_key


class Command(BaseCommand):
    help = "Gera DJANGO_SECRET_KEY e DJANGO_ADMIN_URL aleatórios."

    def handle(self, *args, **options):
        secret_key = get_random_secret_key()
        admin_url = secrets.token_urlsafe(16).replace("_", "").replace("-", "") + "/"

        self.stdout.write(self.style.SUCCESS("Chaves geradas com sucesso:"))
        self.stdout.write(f"Django_SECRET_KEY={secret_key}")
        self.stdout.write(f"DJANGO_ADMIN_URL={admin_url}")

        env_example = Path(".env.example")
        env_file = Path(".env")
        if env_example.exists() or env_file.exists():
            self.stdout.write("")
            self.stdout.write(
                "Cole esses valores no arquivo .env (ou .env.example) "
                "substituindo os existentes."
            )
            self.stdout.write(
                "Dica: evite commitar o .env com chaves reais em repositórios públicos."
            )
