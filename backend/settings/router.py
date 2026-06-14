"""Ajustes editables desde la WEB (Telegram, etc.). Persisten cifrados en SQLite.

TODO(prod): proteger con auth (Depends get_current_user) — ver AGENTS.md §9.
"""
from fastapi import APIRouter
from pydantic import BaseModel

import notify
from store import get_telegram, set_telegram

router = APIRouter(prefix="/api/settings", tags=["settings"])


class TelegramIn(BaseModel):
    bot_token: str | None = None  # opcional: si no se manda, se conserva el guardado
    chat_id: str | None = None


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
