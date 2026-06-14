"""Endpoint pasivo: lee snapshot y NO toca Netezza (DEVELOPMENT.md)."""


def test_space_lee_snapshot_sin_tocar_netezza(tmp_db, monkeypatch):
    # cualquier intento de query a Netezza debe romper el test
    import netezza.connection as conn

    def _fail(*a, **k):
        raise AssertionError("el endpoint pasivo NO debe consultar Netezza")

    monkeypatch.setattr(conn, "execute_query", _fail)

    from store import save_snapshot

    save_snapshot("space_overview", {"databases": [{"db": "PROD", "gb": 42.0, "table_count": 3}]})

    from fastapi.testclient import TestClient

    import main

    with TestClient(main.app) as client:
        r = client.get("/api/monitoring/space")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["data"]["databases"][0]["db"] == "PROD"
    assert body["age_seconds"] is not None


def test_metrica_sin_snapshot_devuelve_empty(tmp_db):
    from fastapi.testclient import TestClient

    import main

    with TestClient(main.app) as client:
        r = client.get("/api/monitoring/health")
    assert r.status_code == 200
    assert r.json()["status"] == "empty"
