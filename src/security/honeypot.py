"""Honeypot de segurança do Findly.

Objetivo
--------
1. **Esconder** o Django Admin em um caminho secreto (``DJANGO_ADMIN_URL``).
2. Transformar o clássico ``/admin/`` em uma **armadilha** que registra, conta
   e (opcionalmente) bloqueia quem tenta acessá-lo — incluindo a captura das
   credenciais digitadas no formulário falso.

Onde os eventos são gravados
----------------------------
- **Log dedicado**: ``logs/security.log`` (com rotação) + console.
- **Redis**: contadores por IP, blocklist e histórico para o management command
  ``python manage.py honeypot_report``.

O módulo **degrada com segurança**: se o Redis estiver indisponível, o acesso
continua sendo registrado no log e a resposta HTTP nunca quebra.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from ipaddress import ip_address

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound

logger = logging.getLogger("findly.security.honeypot")

# Chaves usadas no Redis (cache "default").
EVENTS_KEY = "honeypot:events"
BLOCKLIST_KEY = "honeypot:blocklist"
HITS_KEY = "honeypot:ip:{ip}:hits"


# ---------------------------------------------------------------------------
# Redis (tolerante a falhas de conexão)
# ---------------------------------------------------------------------------
def _redis():
    """Retorna o cliente Redis do cache ``default`` (django-redis)."""
    from django_redis import get_redis_connection

    return get_redis_connection("default")


# ---------------------------------------------------------------------------
# Identificação de rede
# ---------------------------------------------------------------------------
def get_client_ip(request: HttpRequest) -> str:
    """Extrai o IP do cliente, respeitando ``X-Forwarded-For`` (proxy)."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def _is_private(ip: str) -> bool:
    try:
        addr = ip_address(ip)
    except ValueError:
        return False
    return addr.is_private or addr.is_loopback or addr.is_link_local


def is_trusted(ip: str) -> bool:
    """IPs que nunca são bloqueados (evita auto-bloqueio em desenvolvimento)."""
    return ip in settings.HONEYPOT_TRUSTED_IPS


# ---------------------------------------------------------------------------
# Blocklist
# ---------------------------------------------------------------------------
def is_blocked(ip: str) -> bool:
    try:
        return bool(_redis().sismember(BLOCKLIST_KEY, ip))
    except Exception:  # Redis indisponível → não bloqueia
        logger.debug("Honeypot: falha ao consultar a blocklist.", exc_info=True)
        return False


def should_block(ip: str) -> bool:
    """Decide se um IP deve ser barrado agora (usado pelo middleware)."""
    if is_trusted(ip):
        return False
    if _is_private(ip) and not settings.HONEYPOT_BLOCK_PRIVATE_IPS:
        return False
    return is_blocked(ip)


def block_ip(ip: str) -> None:
    try:
        _redis().sadd(BLOCKLIST_KEY, ip)
        logger.warning("Honeypot: IP bloqueado -> %s", ip)
    except Exception:
        logger.debug("Honeypot: falha ao bloquear o IP %s.", ip, exc_info=True)


def unblock_ip(ip: str) -> bool:
    try:
        return bool(_redis().srem(BLOCKLIST_KEY, ip))
    except Exception:
        return False


def blocked_ips() -> list[str]:
    try:
        members = _redis().smembers(BLOCKLIST_KEY)
    except Exception:
        return []
    return sorted(m.decode() if isinstance(m, bytes) else m for m in members)


# ---------------------------------------------------------------------------
# Contadores e histórico de eventos
# ---------------------------------------------------------------------------
def _register_hit(ip: str) -> int:
    try:
        conn = _redis()
        key = HITS_KEY.format(ip=ip)
        hits = conn.incr(key)
        conn.expire(key, settings.HONEYPOT_BLOCK_TTL_SECONDS)
        return int(hits)
    except Exception:
        return 0


def _store_event(event: dict) -> None:
    try:
        conn = _redis()
        conn.lpush(EVENTS_KEY, json.dumps(event, ensure_ascii=False))
        conn.ltrim(EVENTS_KEY, 0, settings.HONEYPOT_MAX_EVENTS - 1)
    except Exception:
        logger.debug("Honeypot: falha ao persistir evento no Redis.", exc_info=True)


def recent_events(limit: int = 50) -> list[dict]:
    try:
        raw = _redis().lrange(EVENTS_KEY, 0, limit - 1)
    except Exception:
        return []
    events: list[dict] = []
    for item in raw:
        if isinstance(item, bytes):
            item = item.decode()
        try:
            events.append(json.loads(item))
        except json.JSONDecodeError:
            continue
    return events


def clear_events() -> None:
    try:
        _redis().delete(EVENTS_KEY)
    except Exception:
        logger.debug("Honeypot: falha ao limpar os eventos.", exc_info=True)


# ---------------------------------------------------------------------------
# Registro de tentativas
# ---------------------------------------------------------------------------
def _password_fingerprint(password: str) -> dict:
    fingerprint = {
        "password_length": len(password),
        "password_sha256": hashlib.sha256(
            password.encode("utf-8", "ignore")
        ).hexdigest(),
    }
    if settings.HONEYPOT_CAPTURE_PASSWORD_PLAINTEXT:
        fingerprint["password"] = password
    return fingerprint


def record_attempt(
    request: HttpRequest, *, kind: str = "hit", extra: dict | None = None
) -> dict:
    """Registra uma tentativa de acesso indevido e aplica o bloqueio se preciso."""
    ip = get_client_ip(request)
    event: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ip": ip,
        "method": request.method,
        "path": request.get_full_path(),
        "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        "referer": request.META.get("HTTP_REFERER", ""),
        "kind": kind,
    }
    if extra:
        event.update(extra)

    logger.warning(
        "Honeypot [%s] ip=%s method=%s path=%s user_agent=%r",
        kind,
        ip,
        event["method"],
        event["path"],
        event["user_agent"],
    )

    _store_event(event)

    hits = _register_hit(ip)
    event["hits"] = hits
    if hits and hits >= settings.HONEYPOT_BLOCK_THRESHOLD:
        block_ip(ip)

    return event


# ---------------------------------------------------------------------------
# Página-isca (login falso)
# ---------------------------------------------------------------------------
def _decoy_login_page(show_error: bool = False) -> str:
    error_html = (
        '<div class="error" role="alert">'
        "Por favor, informe um usuário e uma senha corretos para uma conta "
        "de equipe. Note que ambos os campos podem ser sensíveis a maiúsculas."
        "</div>"
        if show_error
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex, nofollow">
    <title>Administração — Acesso restrito</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0; min-height: 100vh; display: flex;
            align-items: center; justify-content: center;
            background: #f1f2f4; color: #33363c;
            font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
        }}
        .card {{
            width: 100%; max-width: 380px; background: #fff;
            border: 1px solid #d9d9de; border-radius: 8px;
            padding: 32px 28px; box-shadow: 0 2px 10px rgba(0,0,0,.06);
        }}
        h1 {{ font-size: 18px; margin: 0 0 4px; }}
        p.sub {{ font-size: 13px; color: #6b6f76; margin: 0 0 22px; }}
        label {{ display: block; font-size: 13px; margin: 14px 0 6px; font-weight: 600; }}
        input {{
            width: 100%; padding: 9px 10px; font-size: 14px;
            border: 1px solid #c6c8cd; border-radius: 5px; outline: none;
        }}
        input:focus {{ border-color: #417690; box-shadow: 0 0 0 2px rgba(65,118,144,.15); }}
        button {{
            width: 100%; margin-top: 22px; padding: 10px; font-size: 14px;
            color: #fff; background: #417690; border: 0; border-radius: 5px;
            cursor: pointer;
        }}
        button:hover {{ background: #365f77; }}
        .error {{
            margin-top: 18px; padding: 10px 12px; font-size: 13px;
            color: #a94442; background: #fce4e4; border: 1px solid #f3c2c2;
            border-radius: 5px;
        }}
        .footer {{ margin-top: 20px; font-size: 11px; color: #9aa0a6; text-align: center; }}
    </style>
</head>
<body>
    <main class="card">
        <h1>Administração</h1>
        <p class="sub">Acesso restrito à equipe autorizada.</p>
        {error_html}
        <form method="post" action="" autocomplete="off">
            <label for="id_username">Usuário</label>
            <input id="id_username" name="username" type="text" autofocus autocomplete="off">
            <label for="id_password">Senha</label>
            <input id="id_password" name="password" type="password" autocomplete="off">
            <button type="submit">Entrar</button>
        </form>
        <div class="footer">Sessão protegida • registrada para auditoria</div>
    </main>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
def admin_honeypot_view(request: HttpRequest) -> HttpResponse:
    """Armadilha do clássico ``/admin/`` (e subrotas)."""
    if settings.HONEYPOT_DELAY_SECONDS > 0:
        # "Tarpit": atrasa deliberadamente para desperdiçar o tempo do atacante.
        time.sleep(settings.HONEYPOT_DELAY_SECONDS)

    if request.method == "POST":
        extra: dict = {}
        if settings.HONEYPOT_LOG_CREDENTIALS:
            username = request.POST.get("username", "")
            password = request.POST.get("password", "")
            extra["attempted_username"] = username[:150]
            extra.update(_password_fingerprint(password))
        record_attempt(request, kind="admin_login_attempt", extra=extra)
        return HttpResponse(
            _decoy_login_page(show_error=True),
            content_type="text/html; charset=utf-8",
        )

    record_attempt(request, kind="admin_access")
    return HttpResponse(
        _decoy_login_page(), content_type="text/html; charset=utf-8"
    )


def scanner_honeypot_view(request: HttpRequest, path: str = "") -> HttpResponse:
    """Iscas genéricas (ex.: /wp-admin, /.env) — apenas registra e devolve 404."""
    record_attempt(request, kind="scanner_probe")
    return HttpResponseNotFound(
        "<h1>Not Found</h1><p>O recurso solicitado não está disponível.</p>",
        content_type="text/html; charset=utf-8",
    )
