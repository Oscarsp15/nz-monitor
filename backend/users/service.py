"""Reglas de administración de usuarios. Sin FastAPI: el router traduce los errores a HTTP.

Salvaguardas (CONTRATO): nadie puede borrarse ni desactivarse a sí mismo, y el sistema nunca
puede quedarse sin administradores activos.
"""
from auth.deps import CurrentUser
from auth.roles import Role
from auth.security import hash_password
from store import (
    UsernameTakenError,
    count_active_admins,
    create_user,
    delete_user,
    get_user,
    list_users,
    update_user,
)


class UserNotFoundError(Exception):
    """El usuario indicado no existe (→ 404)."""


class UserRuleError(Exception):
    """Regla de negocio violada: nombre repetido, último admin, auto-baja… (→ 400)."""


def public(row: dict) -> dict:
    """Proyección segura: nunca sale `password_hash` de aquí (AGENTS §9)."""
    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "active": bool(row["active"]),
        "must_change_password": bool(row["must_change_password"]),
        "created_at": row["created_at"],
        "last_login_at": row["last_login_at"],
    }


def listing() -> list[dict]:
    return [public(r) for r in list_users()]


def _require(user_id: int) -> dict:
    row = get_user(user_id)
    if row is None:
        raise UserNotFoundError("El usuario no existe")
    return row


def _check_last_admin(row: dict, *, new_role: str | None = None,
                      new_active: bool | None = None) -> None:
    """Impide dejar el sistema sin administradores activos."""
    was_active_admin = row["role"] == "admin" and bool(row["active"])
    if not was_active_admin:
        return
    still_active_admin = (new_role or row["role"]) == "admin" and (
        row["active"] if new_active is None else new_active
    )
    if still_active_admin:
        return
    if count_active_admins(exclude_id=row["id"]) == 0:
        raise UserRuleError(
            "No puedes dejar el sistema sin administradores activos: crea o activa otro "
            "administrador antes de hacer este cambio.",
        )


def create(username: str, password: str, role: Role) -> dict:
    try:
        row = create_user(username, hash_password(password), role, must_change_password=True)
    except UsernameTakenError as e:
        raise UserRuleError(f"Ya existe un usuario llamado '{username}'") from e
    return public(row)


def update(actor: CurrentUser, user_id: int, *, role: Role | None = None,
           active: bool | None = None, password: str | None = None) -> dict:
    row = _require(user_id)
    if actor.id == user_id and active is False:
        raise UserRuleError("No puedes desactivar tu propio usuario")
    _check_last_admin(row, new_role=role, new_active=active)
    # reseteo de contraseña por un admin → el usuario deberá cambiarla al entrar
    pw_hash = hash_password(password) if password else None
    updated = update_user(
        user_id, role=role, active=active, password_hash=pw_hash,
        must_change_password=True if password else None,
    )
    if updated is None:  # pragma: no cover — carrera imposible en un proceso
        raise UserNotFoundError("El usuario no existe")
    return public(updated)


def remove(actor: CurrentUser, user_id: int) -> None:
    row = _require(user_id)
    if actor.id == user_id:
        raise UserRuleError("No puedes borrar tu propio usuario")
    _check_last_admin(row, new_active=False)
    delete_user(user_id)
