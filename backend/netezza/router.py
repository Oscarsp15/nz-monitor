"""Endpoints de observabilidad de Netezza (router fino; la lógica vive en service.py).

`fresh=true` = botón "Actualizar ahora": salta la caché y consulta Netezza en vivo (AGENTS §2/§8).
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
def overview(db: str | None = None, fresh: bool = False):
    return service.overview(db, fresh)


@router.get("/db_summary")
def db_summary(db: str | None = None, fresh: bool = False):
    return service.db_summary(db, fresh)


@router.get("/dataslices")
def dataslices(fresh: bool = False):
    return service.dataslices(fresh)


@router.get("/owners")
def owners(db: str | None = None, fresh: bool = False):
    return service.owners(db, fresh)


@router.get("/tables")
def tables(db: str | None = None, order: str = "space", page: int = 0,
           fresh: bool = False, q: str | None = None):
    return service.tables(db, order, page, fresh, q)


@router.get("/table")
def table_detail(objid: int, table: str):
    return service.table_detail(objid, table)


@router.get("/table/slices")
def table_slices(objid: int):
    return service.table_slices(objid)


@router.get("/dataslice/tables")
def dataslice_tables(ds: int, page: int = 0, fresh: bool = False):
    return service.tables_on_dataslice(ds, page, fresh)
