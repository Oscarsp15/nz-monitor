"""Alertas inteligentes con Groq (opcional). Genera una recomendación accionable a partir
del dataslice saturado y las tablas peor distribuidas que lo cargan.

Reusa lo aprendido en el DAG: endpoint OpenAI-compat de Groq + User-Agent de navegador
(Cloudflare banea el UA de urllib con 403). Tolerante a fallos: si algo falla, no rompe la alerta.
"""
import json
import logging
import re
import urllib.request

from netezza import service
from store import get_groq

log = logging.getLogger("collector")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# Cloudflare delante de Groq rechaza el UA de urllib (403 code 1010) → UA de navegador.
GROQ_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# heurística del DAG: tablas "scratch" (borrables) vs en uso (redistribuir)
SCRATCH = re.compile(r"(BORRAR|_BKP|BCKUP|PRUEBA|MALO|^TMP_|^TEMP|^TEMPO_)", re.I)


def enabled() -> bool:
    key, _, on = get_groq()
    return bool(key and on)


def ask(prompt: str, max_tokens: int = 300) -> str | None:
    """Llama a Groq y devuelve el texto, o None si falla / no hay key."""
    key, model, _ = get_groq()
    if not key:
        return None
    payload = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(  # noqa: S310 (URL fija de Groq, https)
        GROQ_URL, data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "User-Agent": GROQ_UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 (URL fija de Groq)
            return json.load(r)["choices"][0]["message"]["content"].strip()
    except Exception as e:  # noqa: BLE001 — la IA nunca rompe la alerta
        log.warning("[groq] %s", e)
        return None


def chat(messages: list[dict], tools: list[dict] | None = None,
         tool_choice: str = "auto", max_tokens: int = 600) -> dict | None:
    """Chat multi-turno con tool-calling (OpenAI-compat). Devuelve el `message` del modelo."""
    key, model, _ = get_groq()
    if not key:
        return None
    body: dict = {"model": model, "max_tokens": max_tokens, "temperature": 0.2,
                  "messages": messages}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = tool_choice
    req = urllib.request.Request(  # noqa: S310 (URL fija de Groq, https)
        GROQ_URL, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "User-Agent": GROQ_UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310
            return json.load(r)["choices"][0]["message"]
    except Exception as e:  # noqa: BLE001
        log.warning("[groq.chat] %s", e)
        return None


def alert_analysis(crit_alerts: list[dict]) -> str | None:
    """Recomendación IA para la alerta crítica más severa (dataslice o disco SFTP)."""
    if not enabled() or not crit_alerts:  # sin IA activa, ni siquiera consultamos
        return None
    worst = max(crit_alerts, key=lambda a: a.get("value", 0))
    if worst.get("kind") == "sftp_disk":
        return _sftp_analysis(worst)
    if worst.get("ds") is not None:
        return _dataslice_analysis(worst)
    return None


def _sftp_analysis(worst: dict) -> str | None:
    from sftp import service as sftp_service
    path = worst.get("path") or "/"
    try:
        top = sftp_service.du_top(path, 8)
        old = sftp_service.old_files(path, 180, "*", 30)
    except Exception as e:  # noqa: BLE001
        log.warning("[groq] sin contexto sftp: %s", e)
        return None
    folders = "; ".join(f"{r['size']} {r['path']}" for r in top) or "n/d"
    prompt = (
        f"Eres administrador de sistemas. El disco SFTP {path} esta al {worst.get('value')}% "
        f"(casi lleno). Carpetas mas pesadas: {folders}. Hay {len(old)} archivos de mas de 180 "
        f"dias. Escribe SOLO 3 lineas en espanol, sin markdown, accionable: que carpetas o "
        f"archivos revisar/limpiar para liberar espacio (usa los datos, no inventes)."
    )
    return ask(prompt)


def _dataslice_analysis(worst: dict) -> str | None:
    ds = worst.get("ds")
    try:
        rows = service.tables_on_dataslice(int(ds), order="skew").get("rows", [])
    except Exception as e:  # noqa: BLE001
        log.warning("[groq] sin contexto de tablas: %s", e)
        rows = []
    mal = [r for r in rows if (r.get("skew") or 0) > 8][:10]
    if not mal:
        return None
    drop = [r for r in mal if SCRATCH.search(r.get("table") or "")]
    redis = [r for r in mal if not SCRATCH.search(r.get("table") or "")]
    gb_drop = sum(float(r.get("gb_ds") or 0) for r in drop)
    gb_redis = sum(float(r.get("gb_ds") or 0) for r in redis)
    top = "; ".join(f"{r['table']} (skew {r['skew']}, {r['gb_ds']}GB en ds)" for r in mal[:6])
    # nota: el texto incluye ejemplos de SQL pero es un PROMPT para la IA, no una query ejecutada
    prompt = (
        f"Eres DBA de Netezza. El dataslice {ds} esta al {worst.get('value')}% (casi lleno). "  # noqa: S608
        f"Tablas peor distribuidas que lo cargan: {top}. De ellas, {len(drop)} parecen "
        f"temporales/scratch ({gb_drop:.2f}GB en este slice, candidatas a DROP) y {len(redis)} "
        f"estan en uso ({gb_redis:.2f}GB, hay que redistribuir por una columna de alta "
        f"cardinalidad o hacer GROOM). Escribe 3 lineas en espanol, tono ejecutivo, sin markdown, "
        f"usando estos numeros (no inventes otros), y al final UNA linea de SQL sugerido "
        f"(GROOM TABLE base..tabla;  o  CREATE TABLE base..tabla_new AS SELECT * FROM base..tabla "
        f"DISTRIBUTE ON (columna);)."
    )
    return ask(prompt)
