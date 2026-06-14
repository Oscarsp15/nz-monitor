"""Store de snapshots: roundtrip save/latest y que devuelve el más reciente."""
from datetime import UTC, datetime, timedelta


def test_save_y_latest_roundtrip(tmp_db):
    from store import latest_snapshot, save_snapshot

    save_snapshot("space_overview", {"databases": [{"db": "X", "gb": 1.5}]})
    snap = latest_snapshot("space_overview")
    assert snap is not None
    assert snap["status"] == "ok"
    assert snap["data"]["databases"][0]["db"] == "X"
    assert snap["collected_at"] is not None


def test_latest_devuelve_el_mas_reciente(tmp_db):
    from store import latest_snapshot, save_snapshot

    t0 = datetime.now(UTC)
    save_snapshot("health", {"v": "viejo"}, collected_at=t0 - timedelta(minutes=5))
    save_snapshot("health", {"v": "nuevo"}, collected_at=t0)
    assert latest_snapshot("health")["data"]["v"] == "nuevo"


def test_latest_vacio_devuelve_none(tmp_db):
    from store import latest_snapshot

    assert latest_snapshot("inexistente") is None
