"""Endpoints de observabilidad de Netezza (router fino; la lógica vive en service.py).

TODO(prod): proteger con auth (Depends get_current_user) — ver AGENTS.md §9.
"""
from fastapi import APIRouter

from config import get_settings
from . import service

router = APIRouter(prefix="/api", tags=["netezza"])
S = get_settings()


@router.get("/databases")
def databases():
    return {"databases": service.databases(), "default": S.netezza_database}


@router.get("/overview")
def overview(db: str | None = None):
    return service.overview(db)


@router.get("/dataslices")
def dataslices():
    return service.dataslices()


@router.get("/owners")
def owners(db: str | None = None):
    return service.owners(db)


@router.get("/tables")
def tables(db: str | None = None, ds: int = 1, order: str = "space", page: int = 0):
    return service.tables(db, ds, order, page)


@router.get("/table")
def table_detail(objid: int, table: str):
    return service.table_detail(objid, table)


@router.get("/table/slices")
def table_slices(objid: int):
    return service.table_slices(objid)
