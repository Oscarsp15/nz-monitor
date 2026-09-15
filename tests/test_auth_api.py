"""API de sesión: estado, login OK/KO, usuario inactivo, token inválido y cambio de contraseña."""
from conftest import ADMIN_PASSWORD, ADMIN_PASSWORD_NEW, ADMIN_USER


def test_status_sin_sesion_no_es_401(client):
    r = client.get("/api/auth/status")
    assert r.status_code == 200
    assert r.json() == {"authenticated": False, "user": None, "role": None,
                        "must_change_password": False}


def test_login_ok_devuelve_token_y_rol(client):
    r = client.post("/api/auth/login",
                    json={"username": ADMIN_USER, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["user"] == ADMIN_USER
    assert body["role"] == "admin"
    assert body["must_change_password"] is True  # admin sembrado del .env: debe estrenarla
    assert body["token"]
    assert "password_hash" not in r.text


def test_login_con_password_mala_es_401(client):
    r = client.post("/api/auth/login", json={"username": ADMIN_USER, "password": "noesesta"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Usuario o contraseña inválidos"


def test_login_usuario_inexistente_es_401(client):
    r = client.post("/api/auth/login", json={"username": "fantasma", "password": "loquesea"})
    assert r.status_code == 401


def test_usuario_inactivo_no_puede_entrar_ni_usar_su_token(client, admin_headers, make_user, login):
    headers = make_user("operario", "operador")
    assert client.get("/api/auth/me", headers=headers).status_code == 200

    uid = client.get("/api/auth/me", headers=headers).json()["id"]
    assert client.patch(f"/api/users/{uid}", headers=admin_headers,
                        json={"active": False}).status_code == 200

    # el token ya emitido deja de valer
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    # y no puede volver a entrar
    r = client.post("/api/auth/login",
                    json={"username": "operario", "password": "contrasena123"})
    assert r.status_code == 401


def test_endpoints_protegidos_sin_token_o_con_token_basura(client):
    for headers in ({}, {"Authorization": "Bearer token.basura"}):
        assert client.get("/api/monitoring/health", headers=headers).status_code == 401
        assert client.get("/api/users", headers=headers).status_code == 401
        assert client.get("/api/settings/sftp", headers=headers).status_code == 401
        assert client.get("/api/stream", headers=headers).status_code == 401


def test_stream_acepta_token_por_query(client, admin_headers):
    """EventSource no manda cabeceras: /api/stream admite ?token= (y solo ese endpoint)."""
    from auth.deps import require_auth_stream

    token = admin_headers["Authorization"].removeprefix("Bearer ")
    assert client.get("/api/stream?token=nope").status_code == 401
    # no se consume el stream (es infinito): se valida la dependencia que lo protege
    assert require_auth_stream(None, token).role == "admin"


def test_me_devuelve_el_usuario_actual(client, admin_headers):
    body = client.get("/api/auth/me", headers=admin_headers).json()
    assert body["username"] == ADMIN_USER
    assert body["role"] == "admin"
    # el fixture ya estrenó la contraseña del admin sembrado (el flag pendiente se cubre en
    # test_auth_bootstrap.py)
    assert body["must_change_password"] is False
    assert "password_hash" not in body


def test_cambio_de_password_limpia_must_change_password(client, admin_headers):
    r = client.post("/api/auth/change-password", headers=admin_headers,
                    json={"current_password": ADMIN_PASSWORD_NEW, "new_password": "nuevaclave1"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert client.get("/api/auth/me", headers=admin_headers).json()["must_change_password"] is False

    # la contraseña vieja ya no sirve y la nueva sí
    assert client.post("/api/auth/login",
                       json={"username": ADMIN_USER,
                             "password": ADMIN_PASSWORD_NEW}).status_code == 401
    assert client.post("/api/auth/login",
                       json={"username": ADMIN_USER,
                             "password": "nuevaclave1"}).status_code == 200


def test_cambio_de_password_con_actual_incorrecta_es_400(client, admin_headers):
    r = client.post("/api/auth/change-password", headers=admin_headers,
                    json={"current_password": "equivocada", "new_password": "nuevaclave1"})
    assert r.status_code == 400


def test_password_nueva_muy_corta_es_422(client, admin_headers):
    r = client.post("/api/auth/change-password", headers=admin_headers,
                    json={"current_password": ADMIN_PASSWORD, "new_password": "corta"})
    assert r.status_code == 422
