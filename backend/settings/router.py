"""Ajustes editables desde la WEB (Telegram, etc.). Persisten cifrados en SQLite.

TODO(prod): proteger con auth (Depends get_current_user) — ver AGENTS.md §9.
"""
from fastapi import APIRouter
from pydantic import BaseModel

import notify
from store import get_groq, get_telegram, set_groq, set_telegram

router = APIRouter(prefix="/api/settings", tags=["settings"])


class TelegramIn(BaseModel):
    bot_token: str | None = None  # opcional: si no se manda, se conserva el guardado
    chat_id: str | None = None


class AiIn(BaseModel):
    api_key: str | None = None  # opcional: si no se manda, se conserva la guardada
    model: str | None = None
    enabled: bool | None = None


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
    return {"enabled": enabled, "model": model, "has_key": bool(key)}


@router.put("/ai")
def ai_put(body: AiIn):
    set_groq(body.api_key, body.model, body.enabled)
    key, model, enabled = get_groq()
    return {"enabled": enabled, "model": model, "has_key": bool(key)}


@router.post("/ai/test")
def ai_test():
    txt = notify.ai.ask("Responde en una sola linea, en espanol: 'Conexion con la IA correcta.'")
    return {"ok": txt is not None, "sample": txt}
