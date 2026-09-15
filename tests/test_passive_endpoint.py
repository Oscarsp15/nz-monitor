"""Endpoint pasivo: lee snapshot y NO toca Netezza (DEVELOPMENT.md). Requiere sesion."""


def test_space_lee_snapshot_sin_tocar_netezza(client, admin_headers, monkeypatch):
    # cualquier intento de query a Netezza debe romper el test
    import netezza.connection as conn

    def _fail(*a, **k):
        raise AssertionError("el endpoint pasivo NO debe consultar Netezza")

    monkeypatch.setattr(conn, "execute_query", _fail)

    from store import save_snapshot

    save_snapshot("space_overview", {"databases": [{"db": "PROD", "gb": 42.0, "table_count": 3}]})

    r = client.get("/api/monitoring/space", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["data"]["databases"][0]["db"] == "PROD"
    assert body["age_seconds"] is not None


def test_metrica_sin_snapshot_devuelve_empty(client, admin_headers):
    r = client.get("/api/monitoring/health", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "empty"


def test_endpoint_pasivo_sin_sesion_es_401(client):
    assert client.get("/api/monitoring/space").status_code == 401
