"""Chat IA en la app (mismo agente que Telegram, con tool-calling sobre Netezza)."""
from fastapi import APIRouter
from pydantic import BaseModel

import notify
from store import get_groq

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ChatIn(BaseModel):
    messages: list[dict]  # [{role: 'user'|'assistant', content: str}]


@router.post("/chat")
def chat(body: ChatIn):
    if not get_groq()[0]:
        return {"answer": None, "error": "IA no configurada. Añade tu API key en Ajustes."}
    turns = [{"role": m.get("role"), "content": str(m.get("content", ""))}
             for m in body.messages if m.get("role") in ("user", "assistant")]
    answer = notify.agent.run_chat(turns)
    return {"answer": answer or "No pude responder ahora mismo."}
