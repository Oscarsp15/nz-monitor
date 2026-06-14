"""Asistente conversacional por Telegram (long-polling, sin exponer nada a Internet).

Lee mensajes con getUpdates (conexión SALIENTE) y responde con Groq + contexto real de Netezza.
Pensado para responder REPLIES a las alertas del bot en el grupo (en el hilo). Por seguridad,
solo atiende el chat configurado.
"""
import json
import logging
import time
import urllib.parse
import urllib.request

from store import get_groq, get_setting, get_telegram

from . import agent

log = logging.getLogger("collector")


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
    # texto plano (sin parse_mode): la respuesta del agente es libre y no debe romper formato
    p = {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}
    if reply_to:
        p["reply_to_message_id"] = reply_to
    _api("sendMessage", p, timeout=15)


def handle_update(update: dict, my_chat: str) -> None:
    msg = update.get("message") or {}
    chat_id = str((msg.get("chat") or {}).get("id", ""))
    text = (msg.get("text") or "").strip()
    if not text or chat_id != str(my_chat):  # seguridad: solo el chat configurado
        return
    replied = ((msg.get("reply_to_message") or {}).get("text")) or None
    # agente con tool-calling: la IA consulta Netezza on-demand
    answer = agent.run_agent(text, replied) or "No pude consultar la IA ahora mismo."
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
