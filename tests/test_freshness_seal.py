"""Revalidación visible (AGENTS §2.1): toda vista de investigación devuelve `at` y `from_cache`.

El frontend pinta el último valor conocido atenuado con "actualizando…" y lo reemplaza al llegar
la consulta real; sin `at`/`from_cache` no puede sellar la frescura ni marcar que está revalidando.
Y `?fresh=true` ("Actualizar ahora") tiene que existir en TODOS ellos, incluido el resumen de
dataslice, que era el único que no lo aceptaba.
"""
import pytest

# (ruta, query string) de cada vista de investigación
INVESTIGACION = [
    ("/api/overview", "db=DESA_MODELOS"),
    ("/api/db_summary", "db=DESA_MODELOS"),
    ("/api/tables", "db=DESA_MODELOS&order=space&page=0"),
    ("/api/tables", "db=*&order=space&page=0"),
    ("/api/owners", "db=DESA_MODELOS"),
    ("/api/dataslices", ""),
    ("/api/dataslice/tables", "ds=1&page=0"),
    ("/api/dataslice/summary", "ds=1"),
    ("/api/table", "objid=1&table=T"),
    ("/api/table/slices", "objid=1"),
]


def _fake_rows(sql: str) -> list[dict]:
    """Respuestas plausibles del catálogo, elegidas por la forma del SQL."""
    s = " ".join(sql.split())
    if "_V_DATABASE" in s:
        return [{"database": "DESA_MODELOS"}]
    if "_V_TABLE_DIST_MAP" in s:
        return [{"objid": 1, "dist": "ID"}]
    if "HISTDB_SUPPORT" in s:
        return [{"tend": "2026-09-14 10:00:00", "usr": "U", "db": "DESA_MODELOS",
                 "sql": "SELECT * FROM T"}]
    if "_V_DSLICE" in s:
        return [{"ds_id": 1, "pct": 10, "gb_used": 1, "gb_size": 2, "ds_status": "Healthy"}]
    if "AS sch" in s:
        return [{"db": "DESA_MODELOS", "sch": "DBO", "owner": "O", "created": "2026-01-01",
                 "gb": "1.0", "skew": "0.5"}]
    if "AS gb_ds" in s:
        return [{"dbname": "DESA_MODELOS", "schema": "DBO", "tablename": "T", "owner": "O",
                 "objid": 1, "skew": "0.5", "gb_ds": "0.1", "gb_total": "1.0"}]
    if "AS skewed" in s and "AS n" in s:
        return [{"n": 5, "skewed": 2}]
    if "AS skewed" in s:
        return [{"table_count": 3, "total_gb": "1.5", "skewed": 1}]
    if "AS tablas" in s:
        return [{"owner": "O", "tablas": 3, "gb": "1.5"}]
    if "AS tablename" in s:
        return [{"dbname": "DESA_MODELOS", "schema": "DBO", "tablename": "T", "owner": "O",
                 "objid": 1, "gb": "1.0", "skew": "0.5", "distribute_on": "ID"}]
    if "AS table_count" in s:
        return [{"table_count": 3, "total_gb": "1.5"}]
    if "SUM(used_bytes)" in s and "AS gb" in s:
        return [{"dsid": 1, "gb": "0.5"}]
    return [{"n": 1}]


@pytest.fixture
def netezza_falso(monkeypatch):
    """Sustituye la capa SQL: aquí se prueba el contrato de la respuesta, no el catálogo."""
    from netezza import service

    service._cache.clear()
    service._dbset = {"DESA_MODELOS"}
    service._dbset_at = float("inf")
    monkeypatch.setattr(service, "run", _fake_rows)
    yield
    service._cache.clear()
    service._dbset = set()
    service._dbset_at = 0.0


@pytest.mark.parametrize(("path", "qs"), INVESTIGACION)
def test_toda_vista_de_investigacion_trae_el_sello(client, admin_headers, netezza_falso, path, qs):
    r = client.get(f"{path}?{qs}", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body.get("at"), int | float), f"{path} no devuelve `at`"
    assert isinstance(body.get("from_cache"), bool), f"{path} no devuelve `from_cache`"


@pytest.mark.parametrize(("path", "qs"), INVESTIGACION)
def test_fresh_true_aceptado_y_marcado_sin_cache(client, admin_headers, netezza_falso, path, qs):
    sep = "&" if qs else ""
    r = client.get(f"{path}?{qs}{sep}fresh=true", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["from_cache"] is False


def test_dataslice_summary_fresh_revuelve_a_consultar(client, admin_headers, netezza_falso):
    """"Actualizar ahora" en la vista de dataslice también debe refrescar los KPI."""
    from netezza import service

    calls = {"n": 0}
    real = service.run

    def contando(sql):
        calls["n"] += 1
        return real(sql)

    service.run = contando
    try:
        assert client.get("/api/dataslice/summary?ds=1", headers=admin_headers).json()["total"] == 5
        primero = calls["n"]
        client.get("/api/dataslice/summary?ds=1", headers=admin_headers)  # cacheado
        assert calls["n"] == primero
        body = client.get("/api/dataslice/summary?ds=1&fresh=true", headers=admin_headers).json()
        assert calls["n"] == primero + 1, "fresh=true debe volver a consultar"
        assert body["from_cache"] is False
    finally:
        service.run = real


def test_viewer_sigue_sin_poder_forzar_fresh_en_el_resumen(client, make_user, netezza_falso):
    headers = make_user("solo_lectura", "viewer")
    assert client.get("/api/dataslice/summary?ds=1", headers=headers).status_code == 200
    assert client.get("/api/dataslice/summary?ds=1&fresh=true", headers=headers).status_code == 403
