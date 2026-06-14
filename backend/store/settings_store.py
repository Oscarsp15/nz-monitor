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


# ─── Telegram (config web) ───
def get_telegram(db_path: Path | None = None) -> tuple[str, str]:
    """(token, chat_id) desde la BD; si falta, cae al .env (fallback)."""
    s = get_settings()
    token = get_setting("telegram_bot_token", db_path) or s.telegram_bot_token
    chat = get_setting("telegram_chat_id", db_path) or s.telegram_chat_id
    return token, chat


def set_telegram(token: str | None, chat_id: str | None, db_path: Path | None = None) -> None:
    if token:  # solo se actualiza si mandan uno nuevo (no se borra al guardar solo el chat)
        set_setting("telegram_bot_token", token, secret=True, db_path=db_path)
    if chat_id is not None:
        set_setting("telegram_chat_id", chat_id, db_path=db_path)
