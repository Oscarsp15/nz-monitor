"""Notificaciones push por Telegram (Bot API). Sin dependencias: usa urllib.

Desactivado si faltan TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID (no rompe el recolector).
`chat_id` puede ser un usuario, un grupo (id negativo) o un canal.
"""
import json
import logging
import urllib.parse
import urllib.request

from store import get_telegram

log = logging.getLogger("collector")


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


def notify_alerts(prev: dict | None, payload: dict | None) -> None:
    """Avisa SOLO de dataslices que ENTRAN en crítico (no en cada ciclo → sin spam)."""
    if not configured() or not payload:
        return
    prev_data = (prev or {}).get("data") or {}
    prev_crit = {a.get("ds") for a in prev_data.get("alerts", []) if a.get("level") == "crit"}
    new_crit = [a for a in payload.get("alerts", [])
                if a.get("level") == "crit" and a.get("ds") not in prev_crit]
    if not new_crit:
        return
    lines = "\n".join(f"🔴 {a['message']}" for a in new_crit)
    text = (f"<b>nz-monitor — alerta</b>\n{lines}\n"
            f"<i>saturación máx. {payload.get('max_dataslice_pct')}% · "
            f"{payload.get('count')} alerta(s) activas</i>")
    send(text)
