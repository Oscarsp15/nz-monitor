"""Sesión: estado, login, usuario actual y cambio de contraseña propia.

La administración de usuarios (alta/baja/roles) vive en `users/` — aquí solo la sesión.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import service
from .deps import AuthUser, MaybeUser
from .schemas import Password
from .security import make_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: Password


@router.get("/status")
def status(user: MaybeUser) -> dict:
    """Estado de sesión. Nunca devuelve 401: el frontend lo usa para decidir si pinta el login."""
    if user is None:
        return {"authenticated": False, "user": None, "role": None,
                "must_change_password": False}
    return {"authenticated": True, "user": user.username, "role": user.role,
            "must_change_password": user.must_change_password}


@router.post("/login")
def login(body: LoginIn) -> dict:
    row = service.authenticate(body.username, body.password)
    if row is None:
        # mismo mensaje para usuario inexistente, contraseña mala o cuenta inactiva
        raise HTTPException(401, "Usuario o contraseña inválidos")
    return {
        "token": make_token(row["username"], row["id"], row["role"]),
        "user": row["username"],
        "role": row["role"],
        "must_change_password": bool(row["must_change_password"]),
    }


@router.get("/me")
def me(user: AuthUser) -> dict:
    return {"id": user.id, "username": user.username, "role": user.role,
            "must_change_password": user.must_change_password}


@router.post("/change-password")
def change_password(body: ChangePasswordIn, user: AuthUser) -> dict:
    if not service.change_own_password(user.id, body.current_password, body.new_password):
        raise HTTPException(400, "La contraseña actual no es correcta")
    return {"ok": True}
