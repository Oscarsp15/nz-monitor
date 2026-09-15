"""Endpoints de administración de usuarios (`/api/users`). SOLO rol admin.

Dominio aparte de `auth/`: `auth/` es la SESIÓN (login, token, contraseña propia) y lo usa
cualquier usuario; esto es ADMINISTRACIÓN de cuentas, con otro permiso y otro ciclo de vida.
Mantiene la estructura por dominio del repo (AGENTS §3/§10).
"""
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.deps import AuthUser, require_role
from auth.roles import Role
from auth.schemas import Password, Username

from . import service

router = APIRouter(prefix="/api/users", tags=["users"],
                   dependencies=[Depends(require_role("admin"))])


class UserOut(BaseModel):
    id: int
    username: str
    role: Role
    active: bool
    must_change_password: bool
    created_at: str
    last_login_at: str | None = None


class UserCreateIn(BaseModel):
    username: Username
    password: Password
    role: Role


class UserPatchIn(BaseModel):
    role: Role | None = None
    active: bool | None = None
    password: Password | None = None


def _guard(fn: Callable[[], Any]) -> Any:
    """Traduce los errores de dominio a HTTP (mismo patrón que `sftp/router.py`)."""
    try:
        return fn()
    except service.UserNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    except service.UserRuleError as e:
        raise HTTPException(400, str(e)) from e


@router.get("")
def list_all() -> dict:
    return {"users": service.listing()}


@router.post("", response_model=UserOut)
def create(body: UserCreateIn) -> Any:
    return _guard(lambda: service.create(body.username, body.password, body.role))


@router.patch("/{user_id}", response_model=UserOut)
def patch(user_id: int, body: UserPatchIn, actor: AuthUser) -> Any:
    return _guard(lambda: service.update(actor, user_id, role=body.role, active=body.active,
                                         password=body.password))


@router.delete("/{user_id}")
def delete(user_id: int, actor: AuthUser) -> dict:
    _guard(lambda: service.remove(actor, user_id))
    return {"ok": True}
