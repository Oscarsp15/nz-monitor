"""Jobs del recolector: golpean Netezza UNA vez y guardan un snapshot en SQLite.

Sin dependencia de APScheduler (eso vive en __main__) → estos jobs son unitariamente testeables.
Cada job es tolerante a fallos: si Netezza no responde, guarda el snapshot como `error`, no rompe
el scheduler (ver ARCHITECTURE.md §2.1).
"""
from collections.abc import Callable
from typing import Any

from cache import get_event_bus
from config import get_settings
from netezza import service
from netezza.connection import test_connection
from store import snapshots

# tipos de métrica (coinciden con metric_type en metric_snapshot)
HEALTH = "health"
SPACE_OVERVIEW = "space_overview"

S = get_settings()


def collect_health() -> Any:
    """Salud de la conexión a Netezza (un ping con timeout)."""
    return test_connection(
        S.netezza_host, S.netezza_port, S.netezza_database, S.netezza_user, S.netezza_password
    )


def collect_space_overview() -> Any:
    """Espacio + nº de tablas por base (query pesada, solo aquí)."""
    return {"databases": service.space_by_db()}


def run_job(metric_type: str, fn: Callable[[], Any], *, credential_id: int | None = None) -> dict:
    """Ejecuta un job, persiste el snapshot y publica un evento. No lanza excepción."""
    try:
        payload = fn()
        status, error = "ok", None
    except Exception as e:  # noqa: BLE001 — tolerante: el scheduler debe seguir vivo
        payload, status, error = None, "error", str(e)
    collected_at = snapshots.save_snapshot(
        metric_type, payload, credential_id=credential_id, status=status, error=error
    )
    get_event_bus().publish(
        "snapshots",
        {"metric_type": metric_type, "status": status, "collected_at": collected_at},
    )
    return {
        "metric_type": metric_type, "status": status, "collected_at": collected_at, "error": error,
    }
