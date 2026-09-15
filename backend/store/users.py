"""Store de usuarios (SQLite, tabla `app_user`) — CRUD puro, sin reglas de negocio.

Comparte archivo y patrón de conexión con `snapshots.py` / `settings_store.py`: el esquema se
crea solo (`CREATE TABLE IF NOT EXISTS`) en cada operación, así el recolector y la API pueden
arrancar en cualquier orden.

Las filas incluyen `password_hash`: NUNCA devolver una fila cruda al frontend (ver AGENTS §9);
quien sirve HTTP debe proyectarla con el modelo Pydantic de `users/service.py`.
"""
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from .snapshots import _connect  # reusa la resolución de ruta/conexión

_SCHEMA = """
CREATE TABLE IF NOT EXISTS app_user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE COLLATE NOCASE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('admin','operador','viewer')),
  active INTEGER NOT NULL DEFAULT 1,
  must_change_password INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  last_login_at TEXT
);
"""


class UsernameTakenError(Exception):
    """Ya existe un usuario con ese nombre (comparación sin distinguir mayúsculas)."""


def _ensure(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


def init_users(db_path: Path | None = None) -> None:
    """Crea la tabla si no existe (idempotente)."""
    with _connect(db_path) as conn:
        _ensure(conn)


def _row(conn: sqlite3.Connection, user_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM app_user WHERE id=?", (user_id,)).fetchone()
    return dict(row) if row else None


def create_user(
    username: str,
    password_hash: str,
    role: str,
    *,
    active: bool = True,
    must_change_password: bool = True,
    db_path: Path | None = None,
) -> dict:
    """Inserta un usuario y devuelve la fila creada. `UsernameTakenError` si el nombre ya existe."""
    now = datetime.now(UTC).isoformat()
    with _connect(db_path) as conn:
        _ensure(conn)
        try:
            cur = conn.execute(
                "INSERT INTO app_user "
                "(username, password_hash, role, active, must_change_password, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (username, password_hash, role, int(active), int(must_change_password), now),
            )
        except sqlite3.IntegrityError as e:
            raise UsernameTakenError(username) from e
        created = _row(conn, int(cur.lastrowid or 0))
    if created is None:  # pragma: no cover — no debería ocurrir tras un INSERT correcto
        raise RuntimeError("no se pudo leer el usuario recién creado")
    return created


def get_user_by_username(username: str, db_path: Path | None = None) -> dict | None:
    with _connect(db_path) as conn:
        _ensure(conn)
        row = conn.execute("SELECT * FROM app_user WHERE username=?", (username,)).fetchone()
    return dict(row) if row else None


def get_user(user_id: int, db_path: Path | None = None) -> dict | None:
    with _connect(db_path) as conn:
        _ensure(conn)
        row = conn.execute("SELECT * FROM app_user WHERE id=?", (user_id,)).fetchone()
    return dict(row) if row else None


def list_users(db_path: Path | None = None) -> list[dict]:
    with _connect(db_path) as conn:
        _ensure(conn)
        rows = conn.execute("SELECT * FROM app_user ORDER BY username COLLATE NOCASE").fetchall()
    return [dict(r) for r in rows]


def count_users(db_path: Path | None = None) -> int:
    with _connect(db_path) as conn:
        _ensure(conn)
        return int(conn.execute("SELECT COUNT(*) AS n FROM app_user").fetchone()["n"])


def count_active_admins(exclude_id: int | None = None, db_path: Path | None = None) -> int:
    """Admins activos, opcionalmente ignorando uno (para simular un cambio antes de aplicarlo)."""
    with _connect(db_path) as conn:
        _ensure(conn)
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM app_user "
            "WHERE role='admin' AND active=1 AND id IS NOT ?",
            (exclude_id,),
        ).fetchone()
    return int(row["n"])


def update_user(
    user_id: int,
    *,
    role: str | None = None,
    active: bool | None = None,
    password_hash: str | None = None,
    must_change_password: bool | None = None,
    db_path: Path | None = None,
) -> dict | None:
    """Actualiza solo los campos recibidos. Devuelve la fila resultante (o None si no existe)."""
    sets: list[str] = []
    args: list[object] = []
    if role is not None:
        sets.append("role=?")
        args.append(role)
    if active is not None:
        sets.append("active=?")
        args.append(int(active))
    if password_hash is not None:
        sets.append("password_hash=?")
        args.append(password_hash)
    if must_change_password is not None:
        sets.append("must_change_password=?")
        args.append(int(must_change_password))
    with _connect(db_path) as conn:
        _ensure(conn)
        if sets:
            args.append(user_id)
            conn.execute(f"UPDATE app_user SET {', '.join(sets)} WHERE id=?", args)  # noqa: S608
        return _row(conn, user_id)


def touch_last_login(user_id: int, db_path: Path | None = None) -> None:
    with _connect(db_path) as conn:
        _ensure(conn)
        conn.execute(
            "UPDATE app_user SET last_login_at=? WHERE id=?",
            (datetime.now(UTC).isoformat(), user_id),
        )


def delete_user(user_id: int, db_path: Path | None = None) -> bool:
    with _connect(db_path) as conn:
        _ensure(conn)
        cur = conn.execute("DELETE FROM app_user WHERE id=?", (user_id,))
    return cur.rowcount > 0
