"""Endpoints PASIVOS: leen el último snapshot de SQLite. NUNCA tocan Netezza (AGENTS §2/§7).

El recolector mantiene los snapshots frescos; aquí solo se sirven, con `collected_at` y
`age_seconds` para el sello de frescura del frontend ("actualizado hace X").
"""
from datetime import UTC, datetime

from fastapi import APIRouter

from collector.jobs import ALERTS, HEALTH, SPACE_OVERVIEW
from store import latest_snapshot, snapshot_history

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


def _serve(metric_type: str) -> dict:
    snap = latest_snapshot(metric_type)
    if snap is None:
        # el recolector aún no ha corrido (o no hay datos todavía)
        return {"metric": metric_type, "status": "empty", "collected_at": None,
                "age_seconds": None, "data": None}
    age = None
    try:
        collected = datetime.fromisoformat(snap["collected_at"])
        age = round((datetime.now(UTC) - collected).total_seconds(), 1)
    except ValueError:
        pass
    return {"metric": metric_type, "status": snap["status"], "collected_at": snap["collected_at"],
            "age_seconds": age, "error": snap["error"], "data": snap["data"]}


@router.get("/health")
def health():
    return _serve(HEALTH)


@router.get("/space")
def space():
    return _serve(SPACE_OVERVIEW)


@router.get("/alerts")
def alerts():
    return _serve(ALERTS)


@router.get("/history/space")
def history_space():
    """Serie temporal del espacio total (suma de bases) para el gráfico de tendencia."""
    pts = []
    for h in snapshot_history(SPACE_OVERVIEW):
        dbs = (h["data"] or {}).get("databases", [])
        pts.append({"at": h["collected_at"],
                    "total_gb": round(sum(d.get("gb", 0) for d in dbs), 2),
                    "tables": sum(d.get("table_count", 0) for d in dbs)})
    return {"points": pts}


@router.get("/history/saturation")
def history_saturation():
    """Serie temporal de la saturación máxima de dataslice y nº de alertas."""
    pts = [{"at": h["collected_at"],
            "max_pct": (h["data"] or {}).get("max_dataslice_pct", 0),
            "alerts": (h["data"] or {}).get("count", 0)}
           for h in snapshot_history(ALERTS)]
    return {"points": pts}
