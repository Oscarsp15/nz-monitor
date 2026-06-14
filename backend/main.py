"""nz-monitor — API de observabilidad de Netezza (FastAPI).

La API solo SIRVE: lee snapshots (pasivo) o consulta en vivo on-demand. El recolector corre
como proceso aparte (`python -m collector`); la API nunca lo arranca (AGENTS §4).
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from monitoring.router import router as monitoring_router
from netezza.router import router as netezza_router
from store import init_db

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


@app.get("/health")
def health():
    return {"status": "ok", "service": "nz-monitor", "role": S.app_role}
