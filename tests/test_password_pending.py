"""Mientras la contraseña esté pendiente de estrenar, la API solo deja usar /api/auth/*.

Sin esto, la pantalla forzada del frontend sería solo cosmética: quien conozca la contraseña
temporal (el admin/admin inicial, o el reseteo hecho por un administrador) podría usar la API
indefinidamente sin cambiarla.
"""
from conftest import ADMIN_PASSWORD, ADMIN_USER


def test_admin_recien_sembrado_no_puede_usar_la_app(client, login):
    headers = login(ADMIN_USER, ADMIN_PASSWORD)

    for path in ("/api/users", "/api/monitoring/space", "/api/settings/sftp"):
        r = client.get(path, headers=headers)
        assert r.status_code == 403, f"{path} → {r.status_code}"
        assert "cambiar" in r.json()["detail"].lower()

    # pero sí puede ver su sesión y estrenar la contraseña
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    r = client.post("/api/auth/change-password", headers=headers,
                    json={"current_password": ADMIN_PASSWORD, "new_password": "estrenada123"})
    assert r.status_code == 200

    # tras estrenarla, el MISMO token ya sirve (el estado se relee de la BD en cada request)
    assert client.get("/api/users", headers=headers).status_code == 200


def test_reseteo_por_admin_vuelve_a_bloquear_al_usuario(client, admin_headers, make_user):
    viewer = make_user("lector", "viewer")
    assert client.get("/api/monitoring/space", headers=viewer).status_code == 200

    uid = next(u["id"] for u in client.get("/api/users", headers=admin_headers).json()["users"]
               if u["username"] == "lector")
    assert client.patch(f"/api/users/{uid}", headers=admin_headers,
                        json={"password": "reseteada123"}).status_code == 200

    # el token viejo deja de servir para la app hasta que estrene la nueva contraseña
    assert client.get("/api/monitoring/space", headers=viewer).status_code == 403
