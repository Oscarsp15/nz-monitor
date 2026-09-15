"""Ajustes en SQLite: cifrado de secretos."""
import sqlite3


def test_secret_cifrado_y_roundtrip(tmp_db):
    from store import get_setting, set_setting

    set_setting("plano", "valor")
    set_setting("token", "secreto123", secret=True)
    assert get_setting("plano") == "valor"
    assert get_setting("token") == "secreto123"

    # el secreto NO se guarda en claro en la BD
    conn = sqlite3.connect(tmp_db)
    raw = conn.execute("SELECT value FROM app_setting WHERE key='token'").fetchone()[0]
    conn.close()
    assert "secreto123" not in raw
