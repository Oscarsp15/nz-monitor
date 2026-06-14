"""nz-monitor — API de observabilidad de Netezza (FastAPI).

La API solo SIRVE: lee snapshots (pasivo) o consulta en vivo on-demand. El recolector corre
como proceso aparte (`python -m collector`); la API nunca lo arranca (AGENTS §4).
"""
import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from aichat.router import router as aichat_router
from config import get_settings
from monitoring.router import router as monitoring_router
from netezza.router import router as netezza_router
from settings.router import router as settings_router
from sftp.router import router as sftp_router
from store import init_db, latest_snapshot

S = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # asegura la tabla de snapshots (compartida con el recolector)
    yield


app = FastAPI(title="nz-monitor", version="2.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in S.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(netezza_router)
app.include_router(monitoring_router)
app.include_router(settings_router)
app.include_router(aichat_router)
app.include_router(sftp_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "nz-monitor", "role": S.app_role}


_STREAM_METRICS = ("health", "space_overview", "alerts")


@app.get("/api/stream")
async def stream():
    """SSE: empuja un evento al cambiar un snapshot (la API vigila SQLite)."""
    async def gen():
        last: dict[str, str | None] = {}
        yield "event: hello\ndata: {}\n\n"
        while True:
            changed = []
            for m in _STREAM_METRICS:
                snap = latest_snapshot(m)
                ts = snap["collected_at"] if snap else None
                if ts and last.get(m) != ts:
                    last[m] = ts
                    changed.append(m)
            yield (f"data: {json.dumps({'changed': changed})}\n\n" if changed
                   else ": keepalive\n\n")
            await asyncio.sleep(5)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
