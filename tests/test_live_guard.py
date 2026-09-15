"""Guardia de consulta en vivo para `viewer` (AGENTS §9). Dos agujeros reales, cerrados:

1. La guardia comparaba el query string contra una lista literal de valores "verdaderos", pero
   pydantic (que es quien convierte `fresh: bool` en el endpoint) acepta además `t`/`y`:
   `?fresh=true` daba 403 y `?fresh=t` daba **200 con la consulta en vivo ejecutada**.
2. `/api/table` y `/api/table/slices` consultan Netezza SIEMPRE y no tienen `fresh`, así que la
   guardia ni los miraba: un `viewer` disparaba 4 consultas reales, incluida la más cara de la app.
"""
import pytest

# Valores que pydantic convierte a True → tienen que dar 403 a un `viewer`.
VERDADEROS = ["true", "True", "TRUE", "t", "T", "y", "Y", "yes", "YES", "on", "ON", "1"]
# Valores que pydantic convierte a False → no fuerzan nada, pasan.
FALSOS = ["false", "False", "f", "F", "n", "N", "no", "off", "0"]


@pytest.fixture
def netezza_espia(monkeypatch):
    """Cuenta cada consulta que saldría a Netezza. Ninguna debe salir para un `viewer`."""
    from netezza import service

    service._cache.clear()
    service._dbset = {"DESA_MODELOS"}
    service._dbset_at = float("inf")
    hits = {"n": 0}

    def fake_run(sql):
        hits["n"] += 1
        s = " ".join(sql.split())
        if "AS sch" in s:
            return [{"db": "DESA_MODELOS", "sch": "DBO", "owner": "O", "created": "2026-01-01",
                     "gb": "1.0", "skew": "0.5"}]
        if "HISTDB_SUPPORT" in s:
            return []
        if "COUNT(*) AS n FROM (SELECT dsid" in s:
            return [{"n": 3}]
        if "SUM(used_bytes)" in s:
            return [{"dsid": 1, "gb": "0.5"}]
        return [{"table_count": 3, "total_gb": "1.5", "skewed": 1, "n": 1}]

    monkeypatch.setattr(service, "run", fake_run)
    yield hits
    service._cache.clear()
    service._dbset = set()
    service._dbset_at = 0.0


# ─── 1) el parser de la guardia no puede discrepar del de FastAPI ───

@pytest.mark.parametrize("valor", VERDADEROS)
def test_viewer_no_puede_forzar_en_vivo_con_ninguna_forma_de_true(
        client, make_user, netezza_espia, valor):
    headers = make_user("lector", "viewer")
    netezza_espia["n"] = 0

    r = client.get(f"/api/db_summary?db=DESA_MODELOS&fresh={valor}", headers=headers)

    assert r.status_code == 403, f"?fresh={valor} esquivó la guardia: {r.status_code}"
    assert netezza_espia["n"] == 0, f"?fresh={valor} llegó a consultar Netezza"


@pytest.mark.parametrize("valor", VERDADEROS)
def test_lo_mismo_para_el_parametro_live(client, make_user, netezza_espia, valor):
    headers = make_user("lector", "viewer")
    assert client.get(f"/api/tables?db=DESA_MODELOS&live={valor}",
                      headers=headers).status_code == 403


@pytest.mark.parametrize("valor", FALSOS)
def test_valores_falsos_no_bloquean_al_viewer(client, make_user, netezza_espia, valor):
    headers = make_user("lector", "viewer")
    r = client.get(f"/api/db_summary?db=DESA_MODELOS&fresh={valor}", headers=headers)
    assert r.status_code == 200, f"?fresh={valor} no fuerza nada y no debería dar {r.status_code}"


@pytest.mark.parametrize("valor", [*VERDADEROS, *FALSOS, "", "si", "sí", "quizá", "2"])
def test_la_guardia_usa_el_mismo_parser_que_el_endpoint(valor):
    """Invariante: si pydantic lo lee como True, la guardia lo considera "en vivo"."""
    from pydantic import TypeAdapter, ValidationError

    from auth.deps import _forces_live

    try:
        esperado = TypeAdapter(bool).validate_python(valor)
    except ValidationError:
        esperado = False  # no llega al endpoint: FastAPI responde 422 antes de consultar nada
    assert _forces_live(valor) is esperado


def test_operador_si_puede_forzar_en_vivo(client, make_user, netezza_espia):
    headers = make_user("operadora", "operador")
    for valor in ("true", "t", "y"):
        assert client.get(f"/api/db_summary?db=DESA_MODELOS&fresh={valor}",
                          headers=headers).status_code == 200


# ─── 2) endpoints que consultan Netezza SIEMPRE (sin `fresh` que mirar) ───

SIEMPRE_EN_VIVO = ["/api/table?objid=1&table=T", "/api/table/slices?objid=1"]


@pytest.mark.parametrize("url", SIEMPRE_EN_VIVO)
def test_viewer_no_entra_al_detalle_de_tabla(client, make_user, netezza_espia, url):
    headers = make_user("lector", "viewer")
    netezza_espia["n"] = 0

    r = client.get(url, headers=headers)

    assert r.status_code == 403, f"{url} deja pasar a un viewer ({r.status_code})"
    assert netezza_espia["n"] == 0, f"{url} consultó Netezza con rol viewer"


@pytest.mark.parametrize("url", SIEMPRE_EN_VIVO)
def test_operador_si_entra_al_detalle_de_tabla(client, make_user, netezza_espia, url):
    headers = make_user("operadora", "operador")
    assert client.get(url, headers=headers).status_code == 200


@pytest.mark.parametrize("url", SIEMPRE_EN_VIVO)
def test_el_detalle_de_tabla_sigue_exigiendo_sesion(client, url):
    assert client.get(url).status_code == 401
