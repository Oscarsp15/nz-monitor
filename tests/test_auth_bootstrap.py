"""Arranque de la auth: migración del login antiguo (KV) y siembra del admin inicial."""
from conftest import ADMIN_PASSWORD, ADMIN_USER


def test_siembra_admin_inicial_con_cambio_forzado(tmp_db):
    from auth.bootstrap import bootstrap_users
    from store import get_user_by_username, list_users

    assert bootstrap_users() == {"migrated": False, "seeded": True}

    admin = get_user_by_username(ADMIN_USER)
    assert admin["role"] == "admin"
    assert admin["active"] == 1
    assert admin["must_change_password"] == 1
    assert len(list_users()) == 1

    # idempotente: un segundo arranque no duplica nada
    assert bootstrap_users() == {"migrated": False, "seeded": False}
    assert len(list_users()) == 1


def test_migra_el_usuario_legado_y_borra_las_claves_del_kv(tmp_db):
    from auth.bootstrap import bootstrap_users
    from auth.security import hash_password
    from store import get_setting, get_user_by_username, list_users, set_setting

    set_setting("auth_user", "dba_viejo")
    set_setting("auth_pass_hash", hash_password("clave-de-antes"))

    assert bootstrap_users() == {"migrated": True, "seeded": False}

    migrado = get_user_by_username("dba_viejo")
    assert migrado["role"] == "admin"
    assert migrado["must_change_password"] == 0  # conserva su contraseña, no se le fuerza
    assert len(list_users()) == 1  # no se siembra el admin de .env: ya hay usuarios
    assert get_setting("auth_user") is None
    assert get_setting("auth_pass_hash") is None


def test_el_usuario_migrado_puede_iniciar_sesion(tmp_db):
    from auth.security import hash_password
    from store import set_setting

    set_setting("auth_user", "dba_viejo")
    set_setting("auth_pass_hash", hash_password("clave-de-antes"))

    from fastapi.testclient import TestClient

    import main

    with TestClient(main.app) as client:  # el lifespan dispara la migración
        r = client.post("/api/auth/login",
                        json={"username": "dba_viejo", "password": "clave-de-antes"})
        assert r.status_code == 200
        assert r.json()["role"] == "admin"
        assert r.json()["must_change_password"] is False
        # el admin de .env NO se creó (ya había un usuario)
        assert client.post("/api/auth/login",
                           json={"username": ADMIN_USER,
                                 "password": ADMIN_PASSWORD}).status_code == 401
