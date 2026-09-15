"""Configuración editable desde la WEB, guardada en SQLite (clave→valor).

Los valores marcados `secret` se cifran en reposo con Fernet (clave derivada de SECRET_KEY).
Es el canal entre la API (que guarda desde la pantalla de Ajustes) y el recolector (que lee),
ambos comparten el mismo archivo SQLite.
"""
import base64
import hashlib
import sqlite3
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from config import get_settings

from .snapshots import _connect  # reusa la resolución de ruta/conexión

_SCHEMA = """
CREATE TABLE IF NOT EXISTS app_setting (
  key    TEXT PRIMARY KEY,
  value  TEXT NOT NULL,
  secret INTEGER NOT NULL DEFAULT 0
);
"""


def _fernet() -> Fernet:
    # clave Fernet determinística a partir de SECRET_KEY (32 bytes urlsafe-b64)
    digest = hashlib.sha256(get_settings().secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _ensure(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


def set_setting(key: str, value: str, *, secret: bool = False, db_path: Path | None = None) -> None:
    stored = _fernet().encrypt(value.encode()).decode() if secret else value
    with _connect(db_path) as conn:
        _ensure(conn)
        conn.execute(
            "INSERT INTO app_setting(key, value, secret) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, secret=excluded.secret",
            (key, stored, 1 if secret else 0),
        )


def get_setting(key: str, db_path: Path | None = None) -> str | None:
    with _connect(db_path) as conn:
        _ensure(conn)
        row = conn.execute("SELECT value, secret FROM app_setting WHERE key=?", (key,)).fetchone()
    if row is None:
        return None
    if row["secret"]:
        try:
            return _fernet().decrypt(row["value"].encode()).decode()
        except InvalidToken:
            return None  # SECRET_KEY cambió → valor ilegible
    return row["value"]


def delete_setting(key: str, db_path: Path | None = None) -> None:
    """Borra una clave del KV (p.ej. al migrar el login antiguo de un solo usuario)."""
    with _connect(db_path) as conn:
        _ensure(conn)
        conn.execute("DELETE FROM app_setting WHERE key=?", (key,))


# ─── SFTP (credenciales cifradas, config web) ───
def get_sftp(db_path: Path | None = None) -> dict:
    return {
        "host": get_setting("sftp_host", db_path) or "",
        "port": int(get_setting("sftp_port", db_path) or 22),
        "user": get_setting("sftp_user", db_path) or "",
        "password": get_setting("sftp_password", db_path) or None,
        "private_key": get_setting("sftp_key", db_path) or None,
        "default_path": get_setting("sftp_default_path", db_path) or "/",
    }


def set_sftp(host: str | None, port: int | None, user: str | None, password: str | None,
             private_key: str | None, default_path: str | None = None,
             db_path: Path | None = None) -> None:
    if host is not None:
        set_setting("sftp_host", host, db_path=db_path)
    if port is not None:
        set_setting("sftp_port", str(port), db_path=db_path)
    if user is not None:
        set_setting("sftp_user", user, db_path=db_path)
    if password:
        set_setting("sftp_password", password, secret=True, db_path=db_path)
    if private_key:
        set_setting("sftp_key", private_key, secret=True, db_path=db_path)
    if default_path is not None:
        set_setting("sftp_default_path", default_path, db_path=db_path)
