"""Arranque de la auth: migra el login antiguo (1 usuario en el KV) y siembra el admin inicial.

Se ejecuta en el `lifespan` de la API y al arrancar el recolector (comparten el mismo SQLite),
es idempotente y no escribe secretos en el log.
"""
import logging
from pathlib import Path

from config import get_settings
from store import (
    count_users,
    create_user,
    delete_setting,
    get_setting,
    get_user_by_username,
    init_users,
)

from .security import hash_password

log = logging.getLogger("auth.bootstrap")

_LEGACY_KEYS = ("auth_user", "auth_pass_hash")


def bootstrap_users(db_path: Path | None = None) -> dict[str, bool]:
    """Deja el sistema con al menos un admin. Devuelve qué se hizo (para tests/logs)."""
    init_users(db_path)
    migrated = _migrate_legacy_user(db_path)
    seeded = _seed_initial_admin(db_path)
    return {"migrated": migrated, "seeded": seeded}


def _migrate_legacy_user(db_path: Path | None) -> bool:
    """Esquema viejo (`auth_user`/`auth_pass_hash` del KV) → usuario `admin`; borra las claves."""
    username = get_setting("auth_user", db_path)
    pass_hash = get_setting("auth_pass_hash", db_path)
    migrated = False
    if username and pass_hash and get_user_by_username(username, db_path) is None:
        # se reusa el hash tal cual: es el mismo formato pbkdf2 de `security.hash_password`
        create_user(username, pass_hash, "admin", must_change_password=False, db_path=db_path)
        migrated = True
        log.info("login antiguo migrado a app_user como admin: %s", username)
    if any(get_setting(k, db_path) is not None for k in _LEGACY_KEYS):
        for key in _LEGACY_KEYS:
            delete_setting(key, db_path)
    return migrated


def _seed_initial_admin(db_path: Path | None) -> bool:
    """Sin ningún usuario → crea el admin inicial de `.env` con cambio de contraseña forzado."""
    if count_users(db_path) > 0:
        return False
    s = get_settings()
    create_user(
        s.admin_user,
        hash_password(s.admin_password),
        "admin",
        must_change_password=True,
        db_path=db_path,
    )
    log.warning(
        "Creado el administrador inicial %r desde ADMIN_USER/ADMIN_PASSWORD. "
        "Debe cambiar la contraseña en el primer inicio de sesión.",
        s.admin_user,
    )
    return True
