"""Endpoints SFTP (en vivo, on-demand). TODO(prod): auth (AGENTS §9)."""
from fastapi import APIRouter, HTTPException

from . import service

router = APIRouter(prefix="/api/sftp", tags=["sftp"])


def _guard(fn):
    try:
        return fn()
    except ValueError as e:  # SFTP no configurado / entrada inválida
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001 — fallo de conexión SSH, etc.
        raise HTTPException(status_code=502, detail=f"SFTP: {e}") from e


@router.get("/health")
def health():
    return _guard(service.health)


@router.get("/disk")
def disk(path: str = "/"):
    return _guard(lambda: service.disk_usage(path))


@router.get("/du")
def du(path: str = "/", top: int = 20):
    return {"rows": _guard(lambda: service.du_top(path, top))}


@router.get("/old-files")
def old_files(path: str = "/", days: int = 90, pattern: str = "*", max: int = 100):
    return {"rows": _guard(lambda: service.old_files(path, days, pattern, max))}


@router.get("/ls")
def ls(path: str = "/"):
    return {"rows": _guard(lambda: service.list_dir(path))}
