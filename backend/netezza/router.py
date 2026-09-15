"""Endpoints de observabilidad de Netezza (router fino; la lógica vive en service.py).

`fresh=true` = botón "Actualizar ahora": salta la caché y consulta Netezza en vivo (AGENTS §2/§8).
Auth: el router se monta con `deny_live_for_viewer` en `main.py` → exige sesión y, si el rol es
`viewer`, rechaza `fresh=true`/`live=true` con 403 (AGENTS §9). Esa guardia mira el query string,
así que un endpoint **sin** `fresh` que consulte Netezza siempre (`/api/table*`) declara además
`require_role("operador")`; si no, un `viewer` lo llamaría sin que nadie lo mire.
"""
from fastapi import APIRouter, Depends

from auth.deps import require_role
from config import get_settings

from . import service

router = APIRouter(prefix="/api", tags=["netezza"])
S = get_settings()

#: Endpoints que consultan Netezza SIEMPRE (no tienen `fresh`, así que `deny_live_for_viewer` ni
#: los mira). Son consulta en vivo por definición → operador+ (AGENTS §9).
_SIEMPRE_EN_VIVO = [Depends(require_role("operador"))]


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


@router.get("/table", dependencies=_SIEMPRE_EN_VIVO)
def table_detail(objid: int, table: str):
    """Detalle de una tabla: 4 consultas reales, una de ellas `table_history` (LIKE sobre
    NZ_QUERY_HISTORY, la más cara de la app). Sin caché → operador+, nunca `viewer`."""
    return service.table_detail(objid, table)


@router.get("/table/slices", dependencies=_SIEMPRE_EN_VIVO)
def table_slices(objid: int):
    return service.table_slices(objid)


@router.get("/dataslice/tables")
def dataslice_tables(ds: int, page: int = 0, fresh: bool = False, order: str = "ds"):
    return service.tables_on_dataslice(ds, page, fresh, order)


@router.get("/dataslice/summary")
def dataslice_summary(ds: int, fresh: bool = False):
    return service.dataslice_summary(ds, fresh)
