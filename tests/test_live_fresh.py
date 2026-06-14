"""Ruta en vivo: ?fresh=true salta la caché y vuelve a consultar (DEVELOPMENT.md)."""


def test_fresh_salta_la_cache(monkeypatch):
    from netezza import service

    service._cache.clear()  # caché limpio para este test

    calls = {"n": 0}

    def fake_run(sql):
        calls["n"] += 1
        return [{"total_gb": 1.0, "table_count": 2}]

    monkeypatch.setattr(service, "run", fake_run)

    service.overview(None)            # 1ª vez: consulta
    assert calls["n"] == 1
    service.overview(None)            # cacheado: no consulta
    assert calls["n"] == 1
    res = service.overview(None, fresh=True)  # fresh: vuelve a consultar
    assert calls["n"] == 2
    assert res["from_cache"] is False
