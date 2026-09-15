"""El SSE no debe anunciar como "cambiado" lo que el navegador acaba de cargar.

El generador arrancaba con la tabla de "último visto" vacía, así que su primer barrido marcaba
todo lo existente como nuevo y el frontend repetía las consultas del montaje (medido: 5
peticiones duplicadas ~90 ms después de entrar).
"""
from datetime import UTC, datetime, timedelta


def test_el_estado_inicial_no_marca_cambios(tmp_db):
    import main
    from store import save_snapshot

    for metrica in main._STREAM_METRICS:
        save_snapshot(metrica, {"v": 1}, status="ok")

    inicial = main._snapshot_timestamps()
    assert all(inicial.values()), "las tres métricas deben tener marca de tiempo"
    # mismo barrido, sin que el recolector haya escrito nada nuevo → nada cambia
    assert [m for m, ts in main._snapshot_timestamps().items() if inicial.get(m) != ts] == []


def test_un_snapshot_nuevo_si_se_anuncia(tmp_db):
    import main
    from store import save_snapshot

    save_snapshot("alerts", {"v": 1}, status="ok")
    inicial = main._snapshot_timestamps()
    save_snapshot("alerts", {"v": 2}, status="ok",
                  collected_at=datetime.now(UTC) + timedelta(seconds=5))
    cambios = [m for m, ts in main._snapshot_timestamps().items() if inicial.get(m) != ts]
    assert "alerts" in cambios
