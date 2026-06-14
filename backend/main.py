"""nz-monitor — API de observabilidad de Netezza (FastAPI)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from netezza.router import router as netezza_router

S = get_settings()
app = FastAPI(title="nz-monitor", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in S.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(netezza_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "nz-monitor"}
