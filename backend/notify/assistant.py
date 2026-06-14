"""Asistente conversacional por Telegram (long-polling, sin exponer nada a Internet).

Lee mensajes con getUpdates (conexión SALIENTE) y responde con Groq + contexto real de Netezza.
Pensado para responder REPLIES a las alertas del bot en el grupo (en el hilo). Por seguridad,
solo atiende el chat configurado.
"""
import json
import logging
import re
import time
import urllib.parse
import urllib.request

from netezza import service
from store import get_groq, get_setting, get_telegram, latest_snapshot

from . import ai

log = logging.getLogger("collector")
_DS_RE = re.compile(r"dataslice\s*(\d+)", re.I)


def assistant_enabled() -> bool:
    token, chat = get_telegram()
    key, _, _ = get_groq()
    return bool(token and chat and key and get_setting("assistant_enabled") == "1")


def _api(method: str, params: dict, timeout: int = 40):
    token, _ = get_telegram()
    if not token:
        return None
    url = f"https://api.telegram.org/bot{token}/{method}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 (URL fija de Telegram)
            return json.loads(r.read() or b"{}")
    except Exception as e:  # noqa: BLE001
        log.warning("[assistant] %s: %s", method, e)
        return None


def _send(chat_id: str, text: str, reply_to: int | None = None) -> None:
    p = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "true"}
    if reply_to:
        p["reply_to_message_id"] = reply_to
    _api("sendMessage", p, timeout=15)


def _context(question: str, replied: str | None) -> str:
    """Resumen en vivo para fundamentar la respuesta (snapshots + ds puntual si se menciona)."""
    parts: list[str] = []
    al = latest_snapshot("alerts")
    if al and al.get("data"):
        d = al["data"]
        parts.append(
            f"Alertas: {d.get('count', 0)} activas, sat. máx {d.get('max_dataslice_pct')}%."
        )
    sp = latest_snapshot("space_overview")
    if sp and sp.get("data"):
        dbs = sorted(sp["data"].get("databases", []), key=lambda x: x.get("gb", 0), reverse=True)
        top = ", ".join(f"{x['db']} {x['gb']}GB" for x in dbs[:3])
        parts.append(f"Top bases por espacio: {top}.")
    # si el mensaje o la alerta citan un dataslice, traer sus tablas peor distribuidas
    m = _DS_RE.search(replied or "") or _DS_RE.search(question or "")
    if m:
        ds = int(m.group(1))
        try:
            rows = service.tables_on_dataslice(ds, order="skew").get("rows", [])[:6]
            if rows:
                tops = "; ".join(f"{r['table']} (skew {r['skew']}, {r['gb_ds']}GB)" for r in rows)
                parts.append(f"Tablas peor distribuidas en dataslice {ds}: {tops}.")
        except Exception as e:  # noqa: BLE001
            log.warning("[assistant] ctx ds %s", e)
    return " ".join(parts) or "Sin datos recientes del recolector."


def handle_update(update: dict, my_chat: str) -> None:
    msg = update.get("message") or {}
    chat_id = str((msg.get("chat") or {}).get("id", ""))
    text = (msg.get("text") or "").strip()
    if not text or chat_id != str(my_chat):  # seguridad: solo el chat configurado
        return
    replied = ((msg.get("reply_to_message") or {}).get("text")) or None
    prompt = (
        "Eres el asistente de nz-monitor (observabilidad de Netezza). Responde breve y claro, en "
        "español, tono técnico, SIN markdown. Básate SOLO en estos datos en vivo:\n"
        f"{_context(text, replied)}\n"
        + (f'El usuario responde a esta alerta: "{replied}".\n' if replied else "")
        + f"Pregunta: {text}"
    )
    answer = ai.ask(prompt, max_tokens=400) or "No pude consultar la IA ahora mismo."
    _send(chat_id, answer, reply_to=msg.get("message_id"))


def run() -> None:
    """Bucle de long-polling. Solo consume mensajes si el asistente está activo."""
    offset: int | None = None
    log.info("[assistant] iniciado (long-polling)")
    while True:
        if not assistant_enabled():
            time.sleep(15)
            continue
        data = _api("getUpdates", {"offset": offset or 0, "timeout": 30}, timeout=40)
        if not data or not data.get("ok"):
            time.sleep(5)
            continue
        _, chat = get_telegram()
        for u in data.get("result", []):
            offset = u["update_id"] + 1
            try:
                handle_update(u, chat)
            except Exception as e:  # noqa: BLE001 — nunca cae el bucle
                log.warning("[assistant] handle: %s", e)
