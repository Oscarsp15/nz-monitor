"""Agente IA con tool-calling: la IA consulta Netezza on-demand para responder con datos exactos.

Las herramientas mapean a funciones ya existentes del service (que sanean entrada). Resultados
compactos para no inflar tokens. Tolerante a fallos: si Groq no responde, devuelve None.
"""
import json
import logging

from netezza import service

from . import ai

log = logging.getLogger("collector")


# ─── herramientas (mapean al service) ───
def _t(r: dict) -> dict:
    return {"db": r.get("db"), "table": r.get("table"), "owner": r.get("owner"),
            "skew": r.get("skew"), "gb": r.get("space_gb"), "dist": r.get("distribute_on")}


def tool_dataslices() -> list[dict]:
    rows = sorted(service.dataslices()["rows"], key=lambda r: r["pct"], reverse=True)[:12]
    return [{"ds": r["id"], "pct": r["pct"], "gb_used": r["gb_used"], "gb_size": r["gb_size"]}
            for r in rows]


def tool_top_skew_tables(db: str | None = None, limit: int = 10) -> list[dict]:
    return [_t(r) for r in service.tables(db, "skew", 0)["rows"][: int(limit or 10)]]


def tool_top_space_tables(db: str | None = None, limit: int = 10) -> list[dict]:
    return [_t(r) for r in service.tables(db, "space", 0)["rows"][: int(limit or 10)]]


def tool_search_tables(text: str, db: str | None = None) -> list[dict]:
    return [_t(r) for r in service.tables(db, "space", 0, False, text)["rows"][:15]]


def tool_db_summary(db: str) -> dict:
    return service.db_summary(db)


def tool_dataslice_tables(ds: int, by: str = "load") -> list[dict]:
    order = "skew" if by == "skew" else "ds"  # load = GB que cargan en ese slice
    rows = service.tables_on_dataslice(int(ds), order=order)["rows"][:12]
    return [{"db": r["db"], "table": r["table"], "owner": r["owner"], "skew": r["skew"],
             "gb_en_ds": r["gb_ds"], "gb_total": r["gb_total"]} for r in rows]


def tool_table_activity(db: str, table: str) -> dict:
    rows = service.tables(db, "space", 0, False, table)["rows"]
    match = next((r for r in rows if (r["table"] or "").upper() == table.upper()),
                 rows[0] if rows else None)
    if not match:
        return {"error": "tabla no encontrada"}
    d = service.table_detail(match["objid"], match["table"])
    sl = service.table_slices(match["objid"])
    return {"db": match["db"], "table": match["table"], "meta": d.get("meta"),
            "dataslices_ocupados": sl.get("occupied"),
            "ultima_actividad": (d.get("history") or [])[:5]}


IMPL = {
    "dataslices": tool_dataslices,
    "top_skew_tables": tool_top_skew_tables,
    "top_space_tables": tool_top_space_tables,
    "search_tables": tool_search_tables,
    "db_summary": tool_db_summary,
    "dataslice_tables": tool_dataslice_tables,
    "table_activity": tool_table_activity,
}


def _fn(name: str, desc: str, props: dict, required: list[str] | None = None) -> dict:
    return {"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": props, "required": required or []}}}


_DB = {"type": "string", "description": "base de datos; omitir = todas"}
TOOLS = [
    _fn("dataslices", "Uso/saturación (%) de los dataslices del clúster.", {}),
    _fn("top_skew_tables", "Tablas peor distribuidas (mayor skew).",
        {"db": _DB, "limit": {"type": "integer"}}),
    _fn("top_space_tables", "Tablas que más espacio ocupan.",
        {"db": _DB, "limit": {"type": "integer"}}),
    _fn("search_tables", "Busca tablas por nombre u owner.",
        {"text": {"type": "string"}, "db": _DB}, ["text"]),
    _fn("db_summary", "Resumen de una base: nº tablas, espacio total, mal distribuidas.",
        {"db": {"type": "string"}}, ["db"]),
    _fn("dataslice_tables", "Tablas que ocupan un dataslice. by='load' (GB que cargan, default) "
        "o by='skew' (peor distribuidas).",
        {"ds": {"type": "integer"}, "by": {"type": "string", "enum": ["load", "skew"]}}, ["ds"]),
    _fn("table_activity", "Metadatos + última actividad (SELECT/INSERT/…) de UNA tabla.",
        {"db": {"type": "string"}, "table": {"type": "string"}}, ["db", "table"]),
]

SYSTEM = (
    "Eres el asistente de nz-monitor, observabilidad de Netezza (IBM). Usa las herramientas para "
    "consultar SIEMPRE datos reales antes de afirmar números o nombres (no inventes). "
    "Contexto del dominio: skew = desigualdad entre los 192 dataslices (0=parejo, alto=mal "
    "distribuida); para liberar/optimizar conviene redistribuir las de mayor skew (por columna de "
    "alta cardinalidad) o GROOM, y DROP si son temporales/scratch.\n"
    "FORMATO para Telegram (texto plano, SIN markdown ni asteriscos): frases cortas; las listas, "
    "una por línea con viñeta '•'; al listar tablas pon 'base.tabla — skew X, Y GB'. Sé conciso."
)


def _loop(messages: list[dict], max_steps: int = 5) -> str | None:
    """Bucle de razonamiento: pide al modelo, ejecuta tools que pida, repite hasta la respuesta."""
    for _ in range(max_steps):
        m = ai.chat(messages, tools=TOOLS)
        if m is None:
            return None
        calls = m.get("tool_calls")
        if not calls:
            return (m.get("content") or "").strip() or None
        messages.append(m)  # mensaje del asistente con las tool_calls
        for tc in calls:
            name = (tc.get("function") or {}).get("name", "")
            try:
                args = json.loads((tc["function"].get("arguments")) or "{}")
            except (ValueError, KeyError):
                args = {}
            fn = IMPL.get(name)
            try:
                result = fn(**args) if fn else {"error": f"herramienta desconocida: {name}"}
            except Exception as e:  # noqa: BLE001 — un fallo de tool no rompe el agente
                result = {"error": str(e)[:200]}
                log.warning("[agent] tool %s: %s", name, e)
            messages.append({"role": "tool", "tool_call_id": tc.get("id"), "name": name,
                             "content": json.dumps(result, default=str)[:3500]})
    m = ai.chat(messages)  # se agotaron los pasos: respuesta final sin tools
    return (m or {}).get("content")


def run_agent(user_text: str, replied: str | None = None) -> str | None:
    """Una sola pregunta (Telegram)."""
    messages: list[dict] = [{"role": "system", "content": SYSTEM}]
    if replied:
        messages.append({"role": "system",
                         "content": f'El usuario responde a esta alerta: "{replied}"'})
    messages.append({"role": "user", "content": user_text})
    return _loop(messages)


def run_chat(turns: list[dict]) -> str | None:
    """Chat con historial (web). `turns` = [{role: user|assistant, content}]."""
    messages: list[dict] = [{"role": "system", "content": SYSTEM}]
    for t in turns[-12:]:
        if t.get("role") in ("user", "assistant") and t.get("content"):
            messages.append({"role": t["role"], "content": str(t["content"])})
    return _loop(messages)
