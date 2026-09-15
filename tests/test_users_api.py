"""Administración de usuarios: CRUD como admin, validación y salvaguardas del CONTRATO."""
from conftest import ADMIN_USER


def _id_of(client, headers, username: str) -> int:
    users = client.get("/api/users", headers=headers).json()["users"]
    return next(u["id"] for u in users if u["username"] == username)


def test_crud_completo_como_admin(client, admin_headers):
    r = client.post("/api/users", headers=admin_headers,
                    json={"username": "ana", "password": "contrasena123", "role": "operador"})
    assert r.status_code == 200
    creado = r.json()
    assert creado["username"] == "ana"
    assert creado["role"] == "operador"
    assert creado["active"] is True
    assert creado["must_change_password"] is True
    assert "password_hash" not in r.text  # nunca salen hashes (AGENTS §9)

    listado = client.get("/api/users", headers=admin_headers).json()["users"]
    assert {u["username"] for u in listado} == {ADMIN_USER, "ana"}
    assert all("password_hash" not in u for u in listado)

    uid = creado["id"]
    r = client.patch(f"/api/users/{uid}", headers=admin_headers, json={"role": "viewer"})
    assert r.status_code == 200
    assert r.json()["role"] == "viewer"

    r = client.patch(f"/api/users/{uid}", headers=admin_headers, json={"active": False})
    assert r.json()["active"] is False

    assert client.delete(f"/api/users/{uid}", headers=admin_headers).json() == {"ok": True}
    assert client.get("/api/users", headers=admin_headers).json()["users"][0]["username"] == (
        ADMIN_USER
    )


def test_reset_de_password_por_admin_fuerza_cambio(client, admin_headers, login):
    client.post("/api/users", headers=admin_headers,
                json={"username": "bruno", "password": "contrasena123", "role": "viewer"})
    uid = _id_of(client, admin_headers, "bruno")

    r = client.patch(f"/api/users/{uid}", headers=admin_headers, json={"password": "otraclave1"})
    assert r.status_code == 200
    assert r.json()["must_change_password"] is True

    headers = login("bruno", "otraclave1")
    assert client.get("/api/auth/me", headers=headers).json()["must_change_password"] is True


def test_validacion_de_entrada(client, admin_headers):
    corto = {"username": "ab", "password": "contrasena123", "role": "viewer"}
    con_espacio = {"username": "an a", "password": "contrasena123", "role": "viewer"}
    pass_corta = {"username": "ana", "password": "1234", "role": "viewer"}
    rol_malo = {"username": "ana", "password": "contrasena123", "role": "jefe"}
    for body in (corto, con_espacio, pass_corta, rol_malo):
        assert client.post("/api/users", headers=admin_headers, json=body).status_code == 422


def test_usuario_repetido_es_400(client, admin_headers):
    body = {"username": "ana", "password": "contrasena123", "role": "viewer"}
    assert client.post("/api/users", headers=admin_headers, json=body).status_code == 200
    r = client.post("/api/users", headers=admin_headers,
                    json={**body, "username": "ANA"})  # UNIQUE COLLATE NOCASE
    assert r.status_code == 400
    assert "Ya existe" in r.json()["detail"]


def test_usuario_inexistente_es_404(client, admin_headers):
    assert client.patch("/api/users/999", headers=admin_headers,
                        json={"role": "viewer"}).status_code == 404
    assert client.delete("/api/users/999", headers=admin_headers).status_code == 404


def test_no_puedes_borrarte_ni_desactivarte_a_ti_mismo(client, admin_headers):
    uid = _id_of(client, admin_headers, ADMIN_USER)

    r = client.patch(f"/api/users/{uid}", headers=admin_headers, json={"active": False})
    assert r.status_code == 400
    assert "propio usuario" in r.json()["detail"]

    r = client.delete(f"/api/users/{uid}", headers=admin_headers)
    assert r.status_code == 400
    assert "propio usuario" in r.json()["detail"]


def test_no_se_puede_quedar_sin_admins_activos(client, admin_headers, make_user):
    otro = make_user("admin2", "admin")
    uid_admin2 = _id_of(client, admin_headers, "admin2")
    uid_admin1 = _id_of(client, admin_headers, ADMIN_USER)

    # con dos admins, degradar a uno se permite
    assert client.patch(f"/api/users/{uid_admin2}", headers=admin_headers,
                        json={"role": "viewer"}).status_code == 200
    # ahora solo queda uno: admin2 (viewer) no puede tocar nada y admin1 no puede autodegradarse
    r = client.patch(f"/api/users/{uid_admin1}", headers=otro, json={"role": "viewer"})
    assert r.status_code == 403

    r = client.patch(f"/api/users/{uid_admin1}", headers=admin_headers, json={"role": "viewer"})
    assert r.status_code == 400
    assert "sin administradores activos" in r.json()["detail"]


def test_borrar_al_ultimo_admin_es_400(client, admin_headers, make_user):
    otro = make_user("admin2", "admin")
    uid_admin1 = _id_of(client, admin_headers, ADMIN_USER)

    # admin2 borra a admin1 → queda uno (permitido)
    assert client.delete(f"/api/users/{uid_admin1}", headers=otro).status_code == 200
    # y ya no puede borrarse a sí mismo (además de ser el último admin)
    uid_admin2 = _id_of(client, otro, "admin2")
    assert client.delete(f"/api/users/{uid_admin2}", headers=otro).status_code == 400
