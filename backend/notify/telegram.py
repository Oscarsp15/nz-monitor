"""Notificaciones push por Telegram (Bot API). Sin dependencias: usa urllib.

Desactivado si faltan TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID (no rompe el recolector).
`chat_id` puede ser un usuario, un grupo (id negativo) o un canal.
"""
import json
import logging
import urllib.parse
import urllib.request
from datetime import UTC, datetime

from store import get_setting, get_telegram, set_setting

log = logging.getLogger("collector")

# recordatorio de un crítico que persiste (minutos) — además del aviso al entrar en crítico
REMIND_AFTER_MIN = 360


def configured() -> bool:
    token, chat = get_telegram()
    return bool(token and chat)


def send(text: str) -> bool:
    """Envía un mensaje (HTML). Devuelve True si Telegram respondió ok. Tolerante a fallos."""
    token, chat = get_telegram()
    if not (token and chat):
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=10) as r:  # noqa: S310 (url fijo de Telegram)
            return json.loads(r.read() or b"{}").get("ok", False)
    except Exception as e:  # noqa: BLE001 — nunca romper el recolector por una notificación
        log.warning("[telegram] no se pudo enviar: %s", e)
        return False


def _minutes_since(iso: str | None) -> float:
    if not iso:
        return 1e9
    try:
        return (datetime.now(UTC) - datetime.fromisoformat(iso)).total_seconds() / 60
    except ValueError:
        return 1e9


def notify_alerts(payload: dict | None) -> None:
    """Notifica dataslices críticos. Estado 'ya avisados' en la BD (no en el snapshot):

    - avisa cuando un dataslice ENTRA en crítico (nuevo respecto a lo ya avisado),
    - reenvía un recordatorio si un crítico PERSISTE más de REMIND_AFTER_MIN,
    - avisa "resuelto" cuando ya no hay críticos.
    Así, al configurar Telegram con críticos ya activos, llegan en el siguiente ciclo.
    """
    if not configured() or not payload:
        return
    crit_alerts = [a for a in payload.get("alerts", [])
                   if a.get("level") == "crit" and a.get("ds") is not None]
    crit = sorted({a["ds"] for a in crit_alerts})
    notified = set(json.loads(get_setting("telegram_notified_crit") or "[]"))
    is_new = any(d not in notified for d in crit)
    mins = _minutes_since(get_setting("telegram_last_notify"))
    is_remind = bool(crit) and mins >= REMIND_AFTER_MIN

    if crit and (is_new or is_remind):
        lines = "\n".join(f"🔴 {a['message']}" for a in crit_alerts)
        prefix = "" if is_new else "(recordatorio) "
        send(f"<b>nz-monitor — {prefix}dataslices críticos</b>\n{lines}\n"
             f"<i>saturación máx. {payload.get('max_dataslice_pct')}%</i>")
        set_setting("telegram_notified_crit", json.dumps(crit))
        set_setting("telegram_last_notify", datetime.now(UTC).isoformat())
    elif not crit and notified:  # se resolvió todo
        send("✅ nz-monitor: sin dataslices críticos.")
        set_setting("telegram_notified_crit", "[]")
        set_setting("telegram_last_notify", datetime.now(UTC).isoformat())
