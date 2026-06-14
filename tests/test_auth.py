"""Login opcional: hash, token y apertura cuando no está configurado."""


def test_password_hash_roundtrip():
    from auth.security import hash_password, verify_password

    h = hash_password("secreto")
    assert verify_password("secreto", h)
    assert not verify_password("malo", h)
    assert not verify_password("secreto", "formato-invalido")


def test_token_roundtrip():
    from auth.security import make_token, verify_token

    assert verify_token(make_token("admin")) == "admin"
    assert verify_token("token.basura") is None


def test_require_auth_abierto_si_no_configurado(tmp_db):
    from auth import require_auth

    assert require_auth(None) is None  # sin login configurado → permite (LAN)
