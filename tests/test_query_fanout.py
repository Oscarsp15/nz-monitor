"""Nº de consultas que sale a Netezza por vista (AGENTS §5: nada de N+1).

Cada consulta al catálogo cuesta ~1 s en el appliance, así que aquí se cuentan, no se cronometran:
si vuelve a aparecer una consulta de más, el test lo caza sin necesidad de VPN.
"""
import pytest


@pytest.fixture
def svc(monkeypatch):
    from netezza import service

    service._cache.clear()
    service._dbset = {"DESA_MODELOS", "DESA_RIESGOS"}
    service._dbset_at = float("inf")
    yield service
    service._cache.clear()
    service._dbset = set()
    service._dbset_at = 0.0


def _recorder(monkeypatch, svc, reply):
    sqls: list[str] = []

    def fake_run(sql):
        sqls.append(" ".join(sql.split()))
        return reply(sqls[-1])

    monkeypatch.setattr(svc, "run", fake_run)
    return sqls


def test_db_summary_es_una_sola_consulta(monkeypatch, svc):
    """Antes: `overview` + `skewed_count` = 2 escaneos del mismo join (2.13 s medidos)."""
    sqls = _recorder(monkeypatch, svc,
                     lambda s: [{"table_count": 11154, "total_gb": "3198.33", "skewed": "751"}])

    res = svc.db_summary("DESA_RIESGOS", fresh=True)

    assert len(sqls) == 1, f"db_summary debe ser UNA consulta, salieron {len(sqls)}: {sqls}"
    assert "SUM(CASE WHEN s.skew>8.0 THEN 1 ELSE 0 END)" in sqls[0]
    assert res == {"table_count": 11154, "total_gb": 3198.33, "skewed": 751,
                   "database": "DESA_RIESGOS", "at": res["at"], "from_cache": False}


def test_tables_todas_las_bases_no_hace_n_mas_1(monkeypatch, svc):
    """Con `db=*` la distribución de la página sale en UNA consulta, no una por base."""
    page = [{"dbname": f"DB{i}", "schema": "DBO", "tablename": f"T{i}", "owner": "O",
             "objid": 1000 + i, "gb": "1.0", "skew": "0.5"} for i in range(7)]

    def reply(s):
        if "_V_TABLE_DIST_MAP" in s:
            return [{"objid": 1000 + i, "dist": f"COL{i},"} for i in range(7)]
        return page

    sqls = _recorder(monkeypatch, svc, reply)

    res = svc.tables("*", "space", 0, fresh=True)

    assert len(sqls) == 2, f"esperadas 2 consultas (página + distribución), salieron {len(sqls)}"
    dist_sql = sqls[1]
    assert dist_sql.count("UNION ALL") == 6  # 7 bases unidas en una sola consulta
    for i in range(7):
        assert f"DB{i}.._V_TABLE_DIST_MAP" in dist_sql
    assert [r["distribute_on"] for r in res["rows"]] == [f"COL{i}" for i in range(7)]


def test_tables_una_sola_base_sigue_siendo_una_consulta(monkeypatch, svc):
    """Con base concreta la distribución va en el JOIN de la propia consulta."""
    sqls = _recorder(monkeypatch, svc, lambda s: [
        {"dbname": "DESA_MODELOS", "schema": "DBO", "tablename": "T", "owner": "O",
         "objid": 1, "gb": "1.0", "skew": "0.5", "distribute_on": "ID"}])

    svc.tables("DESA_MODELOS", "space", 0, fresh=True)

    assert len(sqls) == 1


def test_dist_falla_y_cae_al_camino_por_base(monkeypatch, svc):
    """Si el UNION se cae (p. ej. una base sin permiso) no se pierde el resto de la página."""
    page = [{"dbname": "DB_OK", "schema": "DBO", "tablename": "A", "owner": "O", "objid": 1,
             "gb": "1.0", "skew": "0.0"},
            {"dbname": "DB_MALA", "schema": "DBO", "tablename": "B", "owner": "O", "objid": 2,
             "gb": "1.0", "skew": "0.0"}]

    def reply(s):
        if "UNION ALL" in s:
            raise RuntimeError("permission denied for DB_MALA")
        if "DB_MALA.._V_TABLE_DIST_MAP" in s:
            raise RuntimeError("permission denied for DB_MALA")
        if "DB_OK.._V_TABLE_DIST_MAP" in s:
            return [{"objid": 1, "dist": "ID"}]
        return page

    _recorder(monkeypatch, svc, reply)

    rows = svc.tables("*", "space", 0, fresh=True)["rows"]

    assert rows[0]["distribute_on"] == "ID"      # la base accesible conserva su distribución
    assert rows[1]["distribute_on"] == "RANDOM"  # la otra degrada, no rompe
