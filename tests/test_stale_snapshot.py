"""Estado `stale`: un snapshot viejo NO puede servirse como si fuera actual (AGENTS §2).

Con el recolector parado, `_serve` reenviaba `status="ok"` para siempre: un dato de 11 horas se
pintaba como fresco. Ahora se compara la edad contra el intervalo del recolector de ESE dato.
"""
from datetime import UTC, datetime, timedelta


def _save_old(metric: str, seconds: int) -> None:
    """Guarda un snapshot y le retrasa la marca de tiempo `seconds` segundos."""
    import sqlite3

    from store import get_db_path, save_snapshot

    save_snapshot(metric, {"x": 1})
    old = (datetime.now(UTC) - timedelta(seconds=seconds)).isoformat()
    con = sqlite3.connect(get_db_path())
    con.execute("UPDATE metric_snapshot SET collected_at=? WHERE metric_type=?", (old, metric))
    con.commit()
    con.close()


def test_snapshot_reciente_sigue_siendo_ok(client, admin_headers):
    from store import save_snapshot

    save_snapshot("health", {"status": "connected"})
    body = client.get("/api/monitoring/health", headers=admin_headers).json()
    assert body["status"] == "ok"
    assert body["stale_after_seconds"] == 90 * 3


def test_snapshot_viejo_se_sirve_como_stale(client, admin_headers):
    _save_old("health", 11 * 3600)  # recolector parado desde hace 11 h
    body = client.get("/api/monitoring/health", headers=admin_headers).json()
    assert body["status"] == "stale", "un dato de 11 h no puede servirse como 'ok'"
    assert body["age_seconds"] > body["stale_after_seconds"]
    assert body["data"] is not None  # se sigue sirviendo el último valor conocido, marcado


def test_el_umbral_depende_del_intervalo_de_cada_metrica(client, admin_headers):
    """600 s es obsoleto para `health` (90 s) pero no para `space_overview` (300 s)."""
    _save_old("health", 600)
    _save_old("space_overview", 600)
    assert client.get("/api/monitoring/health", headers=admin_headers).json()["status"] == "stale"
    assert client.get("/api/monitoring/space", headers=admin_headers).json()["status"] == "ok"


def test_un_error_del_recolector_no_se_tapa_con_stale(client, admin_headers):
    from store import save_snapshot

    save_snapshot("alerts", None, status="error", error="VPN caída")
    body = client.get("/api/monitoring/alerts", headers=admin_headers).json()
    assert body["status"] == "error"
    assert body["error"] == "VPN caída"


def test_metrica_sin_snapshot_expone_su_umbral(client, admin_headers):
    body = client.get("/api/monitoring/alerts", headers=admin_headers).json()
    assert body["status"] == "empty"
    assert body["stale_after_seconds"] == 180 * 3
