"""Recolector: cada job hace upsert del snapshot y publica un evento (DEVELOPMENT.md)."""


class _FakeBus:
    def __init__(self):
        self.events = []

    def publish(self, channel, payload):
        self.events.append((channel, payload))


def test_run_job_ok_guarda_snapshot_y_publica(tmp_db, monkeypatch):
    from collector import jobs
    from store import latest_snapshot

    bus = _FakeBus()
    monkeypatch.setattr(jobs, "get_event_bus", lambda: bus)

    result = jobs.run_job("health", lambda: {"status": "connected"})

    assert result["status"] == "ok"
    snap = latest_snapshot("health")
    assert snap["status"] == "ok"
    assert snap["data"] == {"status": "connected"}
    assert bus.events and bus.events[0][0] == "snapshots"
    assert bus.events[0][1]["metric_type"] == "health"


def test_run_job_tolera_fallo_de_netezza(tmp_db, monkeypatch):
    from collector import jobs
    from store import latest_snapshot

    bus = _FakeBus()
    monkeypatch.setattr(jobs, "get_event_bus", lambda: bus)

    def boom():
        raise RuntimeError("Netezza caído")

    result = jobs.run_job("space_overview", boom)

    assert result["status"] == "error"
    snap = latest_snapshot("space_overview")
    assert snap["status"] == "error"
    assert "Netezza" in snap["error"]
    assert bus.events  # incluso en error, se publica el evento
