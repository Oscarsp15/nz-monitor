"""Lógica de observabilidad de Netezza. Usa el pool de connection.py y las queries de queries.py.

Caché-aside simple (TTL) para endpoints pasivos; investigación (detalle) siempre en vivo.
TODO(prod): mover a recolector + store (ver ARCHITECTURE.md) y credenciales del store cifrado.
"""
import re
import time
from collections import defaultdict

from config import get_settings
from . import queries as q
from .connection import execute_query

S = get_settings()

_cache: dict = {}
_dbset: set[str] = set()
_dbset_at: float = 0.0


def run(sql: str) -> list[dict]:
    # vistas cross-DB -> una conexión a la BD por defecto sirve para todas las bases
    return execute_query(S.netezza_host, S.netezza_port, S.netezza_database,
                         S.netezza_user, S.netezza_password, sql)


def _cached(key, ttl, producer):
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[1] < ttl:
        return hit[0], hit[1], True
    val = producer()
    _cache[key] = (val, now)
    return val, now, False


# ─── catálogo (validación de entrada) ───
def databases() -> list[str]:
    global _dbset, _dbset_at
    if _dbset and time.time() - _dbset_at < 300:
        return sorted(_dbset)
    names = [r["database"] for r in run(q.SQL_DATABASES)]
    _dbset = set(names)
    _dbset_at = time.time()
    return names


def safe_db(db: str | None) -> str | None:
    if db in (None, "", "*"):
        return None  # todas las bases
    if not _dbset:
        databases()
    return db if db in _dbset else S.netezza_database


# ─── pasivos ───
def overview(db: str | None):
    db = safe_db(db)
    data, at, cached = _cached(("ov", db), S.overview_ttl, lambda: run(q.overview(db))[0])
    return {"data": {"total_gb": float(data["total_gb"] or 0), "table_count": int(data["table_count"] or 0)},
            "database": db, "at": at, "from_cache": cached}


def dataslices():
    rows, at, cached = _cached(("ds",), S.dataslices_ttl, lambda: run(q.SQL_DSLICE))
    out = [{"id": int(r["ds_id"]), "pct": round(float(r["pct"] or 0), 2),
            "gb_used": float(r["gb_used"] or 0), "gb_size": float(r["gb_size"] or 0),
            "status": r["ds_status"]} for r in rows]
    return {"rows": out, "at": at, "from_cache": cached}


def owners(db: str | None):
    db = safe_db(db)
    rows, at, cached = _cached(("ow", db), S.tables_ttl, lambda: run(q.owners(db)))
    out = [{"owner": r["owner"], "tablas": int(r["tablas"] or 0), "gb": float(r["gb"] or 0)} for r in rows]
    return {"rows": out, "database": db, "at": at, "from_cache": cached}


def tables(db: str | None, ds: int, order: str, page: int):
    db = safe_db(db)
    ds = ds if 0 < ds < 100000 else 1
    order = order if order in q.ORDER_COL else "space"
    page = max(0, page)
    key = ("tb", db, ds, order, page)

    def produce():
        rows = run(q.tables(db, ds, order, page * q.PAGE))
        has_next = len(rows) > q.PAGE
        rows = rows[:q.PAGE]
        norm = [{"db": r.get("dbname"), "schema": r.get("schema"), "table": r.get("tablename"),
                 "owner": r.get("owner"), "objid": int(r.get("objid") or 0),
                 "distribute_on": (r.get("distribute_on") or "RANDOM").strip().strip(",").strip() or "RANDOM",
                 "space_gb": float(r.get("gb") or 0), "skew": float(r.get("skew") or 0),
                 "gb_ds": float(r.get("gb_ds") or 0)} for r in rows]
        if db is None and norm:  # 2ª pasada de distribución por base (todas las bases)
            bydb = defaultdict(list)
            for n in norm:
                bydb[n["db"]].append(n["objid"])
            for dbn, ids in bydb.items():
                idlist = ",".join(str(i) for i in ids if i)
                if not idlist:
                    continue
                try:
                    dm = {int(r["objid"]): (r["dist"] or "").strip().strip(",").strip() or "RANDOM"
                          for r in run(q.dist_for_ids(dbn, idlist))}
                    for n in norm:
                        if n["db"] == dbn:
                            n["distribute_on"] = dm.get(n["objid"], "RANDOM")
                except Exception:
                    pass
        return {"rows": norm, "has_next": has_next}

    val, at, cached = _cached(key, S.tables_ttl, produce)
    return {**val, "database": db, "ds": ds, "order": order, "page": page, "at": at, "from_cache": cached}


# ─── investigación (en vivo, sin caché) ───
def _classify(sql: str) -> str:
    s = (sql or "").lstrip().upper()
    for kw in ("DROP", "TRUNCATE", "INSERT", "UPDATE", "DELETE", "CREATE", "GROOM", "ALTER", "SELECT"):
        if s.startswith(kw):
            return kw
    return "OTRO"


def table_detail(objid: int, table: str):
    out: dict = {"objid": objid, "table": table}
    try:
        m = run(q.table_meta(objid))
        out["meta"] = m[0] if m else None
    except Exception as e:
        out["meta_error"] = str(e)
    tname = re.sub(r"[^A-Za-z0-9_]", "", table or "").upper()
    try:
        h = run(q.table_history(tname))
        out["history"] = [{"tend": str(r["tend"]), "user": r["usr"], "db": r["db"],
                           "verb": _classify(r["sql"]), "sql": (r["sql"] or "").strip()} for r in h]
    except Exception as e:
        out["history_error"] = str(e)
    return out


def table_slices(objid: int):
    rows = run(q.table_slices(objid))
    return {"slices": [{"ds": int(r["dsid"]), "gb": float(r["gb"])} for r in rows]}
