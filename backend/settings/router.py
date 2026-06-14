"""Ajustes editables desde la WEB (Telegram, etc.). Persisten cifrados en SQLite.

TODO(prod): proteger con auth (Depends get_current_user) — ver AGENTS.md §9.
"""
from fastapi import APIRouter
from pydantic import BaseModel

import notify
from sftp import service as sftp_service
from store import (
    get_groq,
    get_setting,
    get_sftp,
    get_telegram,
    set_groq,
    set_setting,
    set_sftp,
    set_telegram,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class TelegramIn(BaseModel):
    bot_token: str | None = None  # opcional: si no se manda, se conserva el guardado
    chat_id: str | None = None


class AiIn(BaseModel):
    api_key: str | None = None  # opcional: si no se manda, se conserva la guardada
    model: str | None = None
    enabled: bool | None = None  # análisis IA en las alertas
    assistant: bool | None = None  # responder mensajes (chat conversacional por Telegram)


@router.get("/telegram")
def telegram_get():
    token, chat = get_telegram()
    return {
        "configured": bool(token and chat),
        "chat_id": chat or "",
        "has_token": bool(token),  # nunca devolvemos el token en claro
    }


@router.put("/telegram")
def telegram_put(body: TelegramIn):
    set_telegram(body.bot_token, body.chat_id)
    token, chat = get_telegram()
    return {"configured": bool(token and chat), "chat_id": chat or "", "has_token": bool(token)}


@router.post("/telegram/test")
def telegram_test():
    ok = notify.send("✅ nz-monitor: mensaje de prueba. Las alertas llegarán aquí.")
    return {"ok": ok}


# ─── IA (Groq) — alertas inteligentes, opcional ───
@router.get("/ai")
def ai_get():
    key, model, enabled = get_groq()
    return {"enabled": enabled, "model": model, "has_key": bool(key),
            "assistant": get_setting("assistant_enabled") == "1"}


@router.put("/ai")
def ai_put(body: AiIn):
    set_groq(body.api_key, body.model, body.enabled)
    if body.assistant is not None:
        set_setting("assistant_enabled", "1" if body.assistant else "0")
    key, model, enabled = get_groq()
    return {"enabled": enabled, "model": model, "has_key": bool(key),
            "assistant": get_setting("assistant_enabled") == "1"}


@router.post("/ai/test")
def ai_test():
    txt = notify.ai.ask("Responde en una sola linea, en espanol: 'Conexion con la IA correcta.'")
    return {"ok": txt is not None, "sample": txt}


# ─── SFTP ───
class SftpIn(BaseModel):
    host: str | None = None
    port: int | None = None
    user: str | None = None
    password: str | None = None  # opcional: si no se manda, se conserva
    private_key: str | None = None
    default_path: str | None = None


def _sftp_state() -> dict:
    c = get_sftp()
    return {"host": c["host"], "port": c["port"], "user": c["user"],
            "has_password": bool(c["password"]), "has_key": bool(c["private_key"]),
            "default_path": c["default_path"], "configured": bool(c["host"] and c["user"])}


@router.get("/sftp")
def sftp_get():
    return _sftp_state()


@router.put("/sftp")
def sftp_put(body: SftpIn):
    set_sftp(body.host, body.port, body.user, body.password, body.private_key, body.default_path)
    return _sftp_state()


@router.post("/sftp/test")
def sftp_test():
    return sftp_service.health()
