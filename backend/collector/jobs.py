"""Jobs del recolector: golpean Netezza UNA vez y guardan un snapshot en SQLite.

Sin dependencia de APScheduler (eso vive en __main__) → estos jobs son unitariamente testeables.
Cada job es tolerante a fallos: si Netezza no responde, guarda el snapshot como `error`, no rompe
el scheduler (ver ARCHITECTURE.md §2.1).
"""
import contextlib
from collections.abc import Callable
from typing import Any

import notify
from cache import get_event_bus
from config import get_settings
from netezza import queries as q
from netezza import service
from netezza.connection import test_connection
from store import snapshots

# tipos de métrica (coinciden con metric_type en metric_snapshot)
HEALTH = "health"
SPACE_OVERVIEW = "space_overview"
ALERTS = "alerts"

# umbrales de saturación de dataslice (%). Alineados al DAG reporte_distribucion_tablas
# (banda de alarma 95–97%): el piso del clúster ronda el 85%, así que avisar a 85% era ruido.
DS_WARN = 90.0
DS_CRIT = 95.0
# umbrales de disco SFTP (%): push (Telegram) al superar 90%
SFTP_WARN = 85.0
SFTP_CRIT = 90.0

S = get_settings()


def collect_health() -> Any:
    """Salud de la conexión a Netezza (un ping con timeout)."""
    return test_connection(
        S.netezza_host, S.netezza_port, S.netezza_database, S.netezza_user, S.netezza_password
    )


def collect_space_overview() -> Any:
    """Espacio + nº de tablas por base (query pesada, solo aquí)."""
    return {"databases": service.space_by_db()}


def _dataslice_alerts() -> tuple[list[dict], float]:
    alerts, max_pct = [], 0.0
    for r in service.run(q.SQL_DSLICE):
        try:
            pct = float(r["pct"])
        except (TypeError, ValueError):
            continue
        max_pct = max(max_pct, pct)
        ds = int(r["ds_id"])
        if pct >= DS_CRIT:
            alerts.append({"level": "crit", "kind": "dataslice", "ds": ds, "key": f"ds:{ds}",
                           "value": round(pct, 1),
                           "message": f"Dataslice {ds} saturado al {pct:.0f}%"})
        elif pct >= DS_WARN:
            alerts.append({"level": "warn", "kind": "dataslice", "ds": ds, "key": f"ds:{ds}",
                           "value": round(pct, 1), "message": f"Dataslice {ds} al {pct:.0f}%"})
    return alerts, max_pct


def _sftp_disk_alerts() -> list[dict]:
    """Alerta de disco SFTP (ruta por defecto) si supera el umbral. Sin SFTP configurado → []."""
    from store import get_sftp  # import perezoso: SFTP es opcional
    cfg = get_sftp()
    if not cfg["host"]:
        return []
    from sftp import service as sftp_service
    path = cfg["default_path"] or "/"
    try:
        d = sftp_service.disk_usage(path)
    except Exception:  # noqa: BLE001 — SFTP caído no rompe las alertas de Netezza
        return []
    if d.get("error"):
        return []
    try:
        pct = float((d.get("use_percent") or "0").replace("%", ""))
    except ValueError:
        return []
    level = "crit" if pct >= SFTP_CRIT else "warn" if pct >= SFTP_WARN else None
    if not level:
        return []
    msg = f"Disco SFTP {path} al {pct:.0f}% ({d.get('used')}/{d.get('size')})"
    return [{"level": level, "kind": "sftp_disk", "key": f"sftp:{path}", "path": path,
             "value": round(pct, 1), "message": msg}]


def collect_alerts() -> Any:
    """Alertas: dataslices saturados + disco SFTP (si está configurado)."""
    alerts, max_pct = _dataslice_alerts()
    alerts += _sftp_disk_alerts()
    alerts.sort(key=lambda a: a["value"], reverse=True)
    return {"alerts": alerts, "count": len(alerts), "max_dataslice_pct": round(max_pct, 1)}


def run_job(metric_type: str, fn: Callable[[], Any], *, credential_id: int | None = None) -> dict:
    """Ejecuta un job, persiste el snapshot, publica un evento y (alertas) notifica. No lanza."""
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
    if status == "ok" and metric_type == ALERTS:
        # una notificación nunca rompe el recolector (notify ya es tolerante a fallos)
        with contextlib.suppress(Exception):
            notify.notify_alerts(payload)
    return {
        "metric_type": metric_type, "status": status, "collected_at": collected_at, "error": error,
    }
