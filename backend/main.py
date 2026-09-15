"""nz-monitor — API de observabilidad de Netezza (FastAPI).

La API solo SIRVE: lee snapshots (pasivo) o consulta en vivo on-demand. El recolector corre
como proceso aparte (`python -m collector`); la API nunca lo arranca (AGENTS §4).
"""
import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from auth import (
    bootstrap_users,
    deny_live_for_viewer,
    deny_password_pending,
    deny_password_pending_stream,
)
from auth.router import router as auth_router
from config import check_secret_key, get_settings
from monitoring.router import router as monitoring_router
from netezza.router import router as netezza_router
from settings.router import router as settings_router
from sftp.router import router as sftp_router
from store import init_db, latest_snapshot
from users.router import router as users_router

S = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_secret_key(S)  # sin clave propia, cualquiera firma un token de admin
    init_db()  # asegura la tabla de snapshots (compartida con el recolector)
    bootstrap_users()  # migra el login antiguo y siembra el admin inicial (auth/bootstrap.py)
    yield


app = FastAPI(title="nz-monitor", version="2.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in S.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Matriz de permisos (ver AGENTS §9). El login es SIEMPRE obligatorio.
app.include_router(auth_router)  # /api/auth/* — login y sesión (cada ruta declara lo suyo)
app.include_router(users_router, dependencies=[Depends(deny_password_pending)])  # admin
app.include_router(settings_router, dependencies=[Depends(deny_password_pending)])  # admin,
# salvo la prueba de conexión (operador+)
app.include_router(monitoring_router,
                   dependencies=[Depends(deny_password_pending)])  # pasivo: viewer+
# Datos en vivo: autenticado y, si el rol es viewer, sin `fresh=true`/`live=true`
_live_guard = [Depends(deny_live_for_viewer), Depends(deny_password_pending)]
app.include_router(netezza_router, dependencies=_live_guard)
app.include_router(sftp_router, dependencies=_live_guard)


@app.get("/health")
def health():
    return {"status": "ok", "service": "nz-monitor", "role": S.app_role}


_STREAM_METRICS = ("health", "space_overview", "alerts")


@app.get("/api/stream", dependencies=[Depends(deny_password_pending_stream)])
async def stream():
    """SSE: empuja un evento al cambiar un snapshot (la API vigila SQLite).

    Requiere sesión. `EventSource` no manda cabeceras, así que este endpoint (y solo este)
    acepta el token por query string: `/api/stream?token=<jwt>`.
    """
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
