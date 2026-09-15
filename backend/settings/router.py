"""Ajustes editables desde la WEB (SFTP). Persisten cifrados en SQLite.

Permisos (AGENTS §9): leer/escribir ajustes es de **admin**; la prueba de conexión abre una
sesión real contra el SFTP, así que es una acción de **operador** (mismo permiso que consultar
en vivo). Por eso el permiso se declara por ruta y no en el router entero.

La gestión de usuarios ya NO vive aquí: está en `/api/users` (ver `users/router.py`).
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth.deps import require_role
from sftp import service as sftp_service
from store import get_sftp, set_sftp

router = APIRouter(prefix="/api/settings", tags=["settings"])

_ADMIN = [Depends(require_role("admin"))]
_OPERADOR = [Depends(require_role("operador"))]


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


@router.get("/sftp", dependencies=_ADMIN)
def sftp_get():
    return _sftp_state()


@router.put("/sftp", dependencies=_ADMIN)
def sftp_put(body: SftpIn):
    set_sftp(body.host, body.port, body.user, body.password, body.private_key, body.default_path)
    return _sftp_state()


@router.post("/sftp/test", dependencies=_OPERADOR)
def sftp_test():
    return sftp_service.health()
