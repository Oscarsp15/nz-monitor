"""Auth (unidad): hash, token con uid/role, jerarquía de roles y revalidación contra la BD."""
import pytest
from fastapi import HTTPException


def test_password_hash_roundtrip():
    from auth.security import hash_password, verify_password

    h = hash_password("secreto")
    assert verify_password("secreto", h)
    assert not verify_password("malo", h)
    assert not verify_password("secreto", "formato-invalido")


def test_token_lleva_uid_y_role():
    from auth.security import make_token, verify_token

    claims = verify_token(make_token("ana", 7, "operador"))
    assert claims["sub"] == "ana"
    assert claims["uid"] == 7
    assert claims["role"] == "operador"
    assert verify_token("token.basura") is None


def test_token_expirado_es_invalido(monkeypatch):
    from config import get_settings

    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "-1")  # ya vencido al emitirse
    get_settings.cache_clear()
    from auth.security import make_token, verify_token

    assert verify_token(make_token("ana", 1, "admin")) is None
    get_settings.cache_clear()


def test_jerarquia_de_roles():
    from auth.roles import role_at_least

    assert role_at_least("admin", "viewer")
    assert role_at_least("operador", "operador")
    assert not role_at_least("viewer", "operador")
    assert not role_at_least("operador", "admin")
    assert not role_at_least("desconocido", "viewer")


def test_require_auth_sin_token_es_401(tmp_db):
    from auth.deps import require_auth

    with pytest.raises(HTTPException) as e:
        require_auth(None)
    assert e.value.status_code == 401


def test_require_auth_falla_si_el_usuario_fue_borrado(tmp_db):
    from auth.deps import require_auth
    from auth.security import hash_password, make_token
    from store import create_user, delete_user

    row = create_user("temporal", hash_password("contrasena123"), "viewer")
    token = make_token(row["username"], row["id"], row["role"])
    assert require_auth(f"Bearer {token}").username == "temporal"

    delete_user(row["id"])
    with pytest.raises(HTTPException) as e:
        require_auth(f"Bearer {token}")
    assert e.value.status_code == 401
