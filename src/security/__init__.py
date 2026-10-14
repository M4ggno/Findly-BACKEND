"""Pacote de segurança do Findly.

Não é um app de domínio — é infraestrutura transversal de proteção:

- :mod:`security.honeypot`   — armadilha em ``/admin/`` e caminhos isca comuns.
- :mod:`security.middleware` — bloqueio de IPs sinalizados pelo honeypot.
- :mod:`security.urls`       — rotas das armadilhas.

O Django Admin é servido em um caminho secreto (``DJANGO_ADMIN_URL``) e o
clássico ``/admin/`` passa a ser uma isca que registra o atacante.

O pacote é registrado em ``INSTALLED_APPS`` apenas para expor o management
command ``honeypot_report``.
"""
