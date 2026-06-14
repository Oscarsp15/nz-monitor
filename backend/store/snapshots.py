"""Store de snapshots de métricas en SQLite (ver ARCHITECTURE.md §3).

El recolector hace `save_snapshot(...)`; los endpoints **pasivos** leen el más reciente con
`latest_snapshot(...)` y devuelven `collected_at` para el sello de frescura ("actualizado hace X").
Es el canal real entre el proceso recolector y la API (comparten el archivo SQLite).
"""
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config import get_settings

# cuántos snapshots conservar por (metric_type, credential_id) — el resto se poda
_KEEP_PER_METRIC = 50

_SCHEMA = """
CREATE TABLE IF NOT EXISTS metric_snapshot (
  id            INTEGER PRIMARY KEY,
  metric_type   TEXT NOT NULL,
  credential_id INTEGER,
  payload_json  TEXT NOT NULL,
  collected_at  TEXT NOT NULL,
  status        TEXT NOT NULL,
  error         TEXT
);
CREATE INDEX IF NOT EXISTS ix_snapshot_lookup
  ON metric_snapshot(metric_type, credential_id, collected_at DESC);
"""


def get_db_path() -> Path:
    """Resuelve la ruta del archivo SQLite desde DATABASE_URL (sqlite:///...)."""
    url = get_settings().database_url
    raw = url.split("sqlite:///", 1)[-1] if url.startswith("sqlite") else url
    return Path(raw).resolve()


def _connect(db_path: Path | None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | None = None) -> None:
    """Crea la tabla e índice si no existen (idempotente)."""
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)


def save_snapshot(
    metric_type: str,
    payload: Any,
    *,
    credential_id: int | None = None,
    status: str = "ok",
    error: str | None = None,
    collected_at: datetime | None = None,
    db_path: Path | None = None,
) -> str:
    """Inserta un snapshot y poda los antiguos. Devuelve el `collected_at` ISO usado."""
    ts = (collected_at or datetime.now(UTC)).isoformat()
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO metric_snapshot "
            "(metric_type, credential_id, payload_json, collected_at, status, error) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (metric_type, credential_id, json.dumps(payload, default=str), ts, status, error),
        )
        # podar: conservar solo los últimos _KEEP_PER_METRIC de este metric+credencial
        conn.execute(
            "DELETE FROM metric_snapshot WHERE metric_type=? "
            "AND IFNULL(credential_id,-1)=IFNULL(?,-1) AND id NOT IN ("
            "  SELECT id FROM metric_snapshot WHERE metric_type=? "
            "  AND IFNULL(credential_id,-1)=IFNULL(?,-1) ORDER BY collected_at DESC LIMIT ?)",
            (metric_type, credential_id, metric_type, credential_id, _KEEP_PER_METRIC),
        )
    return ts


def snapshot_history(
    metric_type: str,
    limit: int = 50,
    db_path: Path | None = None,
) -> list[dict]:
    """Serie temporal: snapshots 'ok' de un tipo, ascendente por fecha (para gráficos)."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT payload_json, collected_at FROM metric_snapshot "
            "WHERE metric_type=? AND status='ok' ORDER BY collected_at DESC LIMIT ?",
            (metric_type, limit),
        ).fetchall()
    out = [{"data": json.loads(r["payload_json"]), "collected_at": r["collected_at"]} for r in rows]
    out.reverse()  # ascendente (más viejo → más nuevo)
    return out


def latest_snapshot(
    metric_type: str,
    credential_id: int | None = None,
    db_path: Path | None = None,
) -> dict | None:
    """Devuelve el snapshot más reciente de un tipo, o None si no hay ninguno."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT payload_json, collected_at, status, error FROM metric_snapshot "
            "WHERE metric_type=? AND IFNULL(credential_id,-1)=IFNULL(?,-1) "
            "ORDER BY collected_at DESC LIMIT 1",
            (metric_type, credential_id),
        ).fetchone()
    if row is None:
        return None
    return {
        "data": json.loads(row["payload_json"]),
        "collected_at": row["collected_at"],
        "status": row["status"],
        "error": row["error"],
    }
