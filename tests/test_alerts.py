"""Alertas: deriva dataslices saturados (ds_percentused es TEXT → parsear)."""


def test_collect_alerts_clasifica_por_umbral(monkeypatch):
    from collector import jobs

    fake = [
        {"ds_id": 1, "pct": "85", "gb_used": 85, "gb_size": 100, "ds_status": "ok"},  # piso normal
        {"ds_id": 2, "pct": "91", "gb_used": 91, "gb_size": 100, "ds_status": "ok"},  # warn (>=90)
        {"ds_id": 3, "pct": "96", "gb_used": 96, "gb_size": 100, "ds_status": "ok"},  # crit (>=95)
    ]
    monkeypatch.setattr(jobs.service, "run", lambda sql: fake)

    out = jobs.collect_alerts()

    assert out["count"] == 2
    assert out["max_dataslice_pct"] == 96.0
    assert out["alerts"][0]["level"] == "crit"  # ordenado por value desc
    assert out["alerts"][1]["level"] == "warn"


def test_collect_alerts_sin_saturacion(monkeypatch):
    from collector import jobs

    monkeypatch.setattr(jobs.service, "run", lambda sql: [{"ds_id": 1, "pct": "10"}])
    out = jobs.collect_alerts()
    assert out["count"] == 0
    assert out["alerts"] == []
