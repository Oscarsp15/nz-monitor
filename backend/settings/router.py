"""Ajustes editables desde la WEB (SFTP, auth). Persisten cifrados en SQLite.

TODO(prod): proteger con auth (Depends get_current_user) — ver AGENTS.md §9.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from auth.security import hash_password
from sftp import service as sftp_service
from store import get_setting, get_sftp, set_setting, set_sftp

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ─── SFTP ───
class SftpIn(BaseModel):
    host: str | None = None
    port: int | None = None
    user: str | None = None
    password: str | None = None  # opcional: si no se manda, se conserva
    private_key: str | None = None
    default_path: str | None = None


def _sftp_state() -> dict:
    c = get_sftp()
    return {"host": c["host"], "port": c["port"], "user": c["user"],
            "has_password": bool(c["password"]), "has_key": bool(c["private_key"]),
            "default_path": c["default_path"], "configured": bool(c["host"] and c["user"])}


@router.get("/sftp")
def sftp_get():
    return _sftp_state()


@router.put("/sftp")
def sftp_put(body: SftpIn):
    set_sftp(body.host, body.port, body.user, body.password, body.private_key, body.default_path)
    return _sftp_state()


@router.post("/sftp/test")
def sftp_test():
    return sftp_service.health()


# ─── Login (opcional) ───
class AuthIn(BaseModel):
    username: str | None = None
    password: str | None = None
    disable: bool | None = None


def _auth_state() -> dict:
    return {"configured": bool(get_setting("auth_user") and get_setting("auth_pass_hash")),
            "user": get_setting("auth_user") or ""}


@router.get("/auth")
def auth_get():
    return _auth_state()


@router.put("/auth")
def auth_put(body: AuthIn):
    if body.disable:
        set_setting("auth_user", "")
        set_setting("auth_pass_hash", "")
    elif body.username and body.password:
        set_setting("auth_user", body.username)
        set_setting("auth_pass_hash", hash_password(body.password))
    return _auth_state()
