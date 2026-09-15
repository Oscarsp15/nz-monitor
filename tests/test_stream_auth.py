"""`/api/stream` (SSE) debe aceptar el token por query: EventSource no manda cabeceras.

Al montar la guardia de "contraseña pendiente" sobre `require_auth` (solo cabecera), FastAPI
resolvía esa dependencia por su cuenta y devolvía 401 aunque el token viajara por `?token=`.

No se consume el stream real (no termina nunca): se prueba la MISMA dependencia que monta
`/api/stream` sobre una ruta espejo, y aparte se comprueba que la ruta real usa esa dependencia.
"""
import pytest
from conftest import ADMIN_PASSWORD, ADMIN_PASSWORD_NEW, ADMIN_USER
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def stream_client(tmp_db):
    """Ruta espejo con la misma guardia que `/api/stream`."""
    from auth import deny_password_pending_stream
    from auth.bootstrap import bootstrap_users

    bootstrap_users()
    app = FastAPI()
    app.include_router(__import__("auth.router", fromlist=["router"]).router)

    @app.get("/espejo", dependencies=[Depends(deny_password_pending_stream)])
    def espejo():
        return {"ok": True}

    with TestClient(app) as c:
        yield c


def _token(client, password: str) -> str:
    r = client.post("/api/auth/login", json={"username": ADMIN_USER, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _estrenar(client) -> str:
    token = _token(client, ADMIN_PASSWORD)
    r = client.post("/api/auth/change-password", headers={"Authorization": f"Bearer {token}"},
                    json={"current_password": ADMIN_PASSWORD, "new_password": ADMIN_PASSWORD_NEW})
    assert r.status_code == 200, r.text
    return token


def test_acepta_el_token_por_query(stream_client):
    token = _estrenar(stream_client)
    assert stream_client.get(f"/espejo?token={token}").status_code == 200


def test_sigue_aceptando_la_cabecera(stream_client):
    token = _estrenar(stream_client)
    assert stream_client.get("/espejo", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_sin_token_es_401(stream_client):
    assert stream_client.get("/espejo").status_code == 401


def test_token_basura_es_401(stream_client):
    assert stream_client.get("/espejo?token=noesuntoken").status_code == 401


def test_password_pendiente_es_403(stream_client):
    token = _token(stream_client, ADMIN_PASSWORD)  # admin sembrado, sin estrenar
    assert stream_client.get(f"/espejo?token={token}").status_code == 403


def test_la_ruta_real_usa_esa_guardia(tmp_db):
    """Evita que la ruta real se separe de lo que prueba el espejo."""
    import main
    from auth import deny_password_pending_stream

    ruta = next(r for r in main.app.routes if getattr(r, "path", None) == "/api/stream")
    calls = [d.call for d in ruta.dependant.dependencies]
    assert deny_password_pending_stream in calls
