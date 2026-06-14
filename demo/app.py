"""
DEMO nz-monitor — datos REALES de Netezza (nzpy).
Reporte de distribución: uso por dataslice, tablas mal distribuidas, carga por dataslice.
Queries basadas en el DAG reporte_distribucion_tablas (vistas cross-DB).
Diseño DESIGN.md + tema claro/oscuro + responsive + PWA + selector de base.
Sin secretos: lee credenciales del entorno  NZ_HOST NZ_PORT NZ_DB NZ_USER NZ_PASS
"""
import os
import re
import time
import threading

import nzpy
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

CFG = dict(
    host=os.environ["NZ_HOST"], port=int(os.environ.get("NZ_PORT", "5480")),
    database=os.environ["NZ_DB"], user=os.environ["NZ_USER"], password=os.environ["NZ_PASS"],
)
HERE = os.path.dirname(__file__)
app = FastAPI(title="nz-monitor demo")
app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")

_conn_lock = threading.Lock()


def query(sql: str) -> list[dict]:
    # vistas cross-DB -> una sola conexión a la BD por defecto sirve para todas las bases
    with _conn_lock:
        conn = nzpy.connect(user=CFG["user"], password=CFG["password"], host=CFG["host"],
                            port=CFG["port"], database=CFG["database"], securityLevel=0)
        try:
            cur = conn.cursor()
            cur.execute(sql)
            if cur.description is None:
                return []
            cols = [d[0].lower() for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
        finally:
            conn.close()


# ─── catálogo de bases válidas (para validar entrada y evitar inyección) ───
_dbs: set[str] = set()


def load_dbs() -> list[str]:
    rows = query("SELECT DATABASE FROM _V_DATABASE ORDER BY DATABASE")
    names = [r["database"] for r in rows]
    _dbs.update(names)
    return names


ALL_DB = "*"


def safe_db(db: str | None) -> str:
    if db == ALL_DB:
        return ALL_DB
    return db if (db and db in _dbs) else CFG["database"]


def _where_db(db: str) -> str:
    return "" if db == ALL_DB else f" AND a.database='{db}'"


ORDER_COL = {"space": "gb", "skew": "skew", "ds": "gb_ds"}


def sql_overview(db: str) -> str:
    return f"""SELECT COUNT(*) AS table_count,
        ROUND(COALESCE(SUM(s.used_bytes),0)/1073741824.0,2) AS total_gb
      FROM _V_OBJ_RELATION_XDB a JOIN _V_SYS_OBJECT_STORAGE_SIZE s ON s.tblid=a.objid
      WHERE a.OBJTYPE='TABLE'{_where_db(db)}"""


PAGE = 25


def sql_tables(db: str, ds: int, order: str, offset: int = 0) -> str:
    oc = ORDER_COL.get(order, "gb")
    # _V_TABLE_DIST_MAP es por-base; en modo "todas las bases" no se puede unir cross-db
    if db == ALL_DB:
        dist_sel, dist_join = "'—'", ""
    else:
        dist_sel = "COALESCE(dm.dist,'RANDOM')"
        dist_join = (f"LEFT JOIN (SELECT objid, TRIM(BOTH ',' FROM "
                     "COALESCE(MAX(CASE WHEN distseqno=1 THEN attname END),'')||','||"
                     "COALESCE(MAX(CASE WHEN distseqno=2 THEN attname END),'')||','||"
                     "COALESCE(MAX(CASE WHEN distseqno=3 THEN attname END),'')) AS dist "
                     f"FROM {db}.._V_TABLE_DIST_MAP GROUP BY objid) dm ON dm.objid=a.objid")
    return f"""
      SELECT a.database AS dbname, a.schema AS schema, a.objname AS tablename, a.owner AS owner, a.objid AS objid,
        ROUND(s.used_bytes/1073741824.0,2) AS gb,
        ROUND(s.skew,2) AS skew,
        ROUND(COALESCE(dsx.bytes_ds,0)/1073741824.0,2) AS gb_ds,
        {dist_sel} AS distribute_on
      FROM _V_OBJ_RELATION_XDB a
      JOIN _V_SYS_OBJECT_STORAGE_SIZE s ON s.tblid=a.objid
      LEFT JOIN (SELECT tblid, SUM(used_bytes) AS bytes_ds
                 FROM _V_SYS_OBJECT_DSLICE_INFO WHERE dsid={ds} GROUP BY tblid) dsx ON dsx.tblid=a.objid
      {dist_join}
      WHERE a.OBJTYPE='TABLE'{_where_db(db)}
      ORDER BY {oc} DESC NULLS LAST LIMIT {PAGE + 1} OFFSET {offset}
    """


SQL_DSLICE = ("SELECT ds_id, ds_percentused AS pct, "
              "ROUND(ds_used/1073741824.0,1) AS gb_used, ds_size AS gb_size, ds_status "
              "FROM _V_DSLICE ORDER BY ds_id")


# ─── caches ───
_ov: dict[str, dict] = {}
_tb: dict[tuple, dict] = {}
_ds = {"data": None, "at": 0.0}
_lock = threading.Lock()


def refresh_overview(db: str) -> dict:
    try:
        row = query(sql_overview(db))[0]
        snap = {"data": {"total_gb": float(row["total_gb"] or 0), "table_count": int(row["table_count"] or 0)},
                "at": time.time(), "status": "ok", "error": None}
    except Exception as e:
        snap = {"data": _ov.get(db, {}).get("data"), "at": time.time(), "status": "error", "error": str(e)}
    with _lock:
        _ov[db] = snap
    return snap


def collector_loop():
    while True:
        try:
            refresh_overview(CFG["database"])
        except Exception:
            pass
        time.sleep(30)


@app.on_event("startup")
def _start():
    try:
        load_dbs()
    except Exception:
        pass
    threading.Thread(target=collector_loop, daemon=True).start()


@app.get("/api/databases")
def databases():
    try:
        return {"databases": load_dbs(), "default": CFG["database"]}
    except Exception as e:
        return {"databases": [CFG["database"]], "default": CFG["database"], "error": str(e)}


@app.get("/api/dataslices")
def dataslices():
    now = time.time()
    if _ds["data"] and now - _ds["at"] < 60:
        return {"rows": _ds["data"], "at": _ds["at"]}
    try:
        rows = query(SQL_DSLICE)
        norm = [{"id": int(r["ds_id"]), "pct": round(float(r["pct"] or 0), 2),
                 "gb_used": float(r["gb_used"] or 0), "gb_size": float(r["gb_size"] or 0),
                 "status": r["ds_status"]} for r in rows]
        _ds.update(data=norm, at=now)
        return {"rows": norm, "at": now}
    except Exception as e:
        return {"rows": [], "error": str(e), "at": now}


@app.get("/api/overview")
def overview(db: str | None = None):
    db = safe_db(db)
    with _lock:
        cur = _ov.get(db)
    if not (cur and cur["status"] == "ok" and time.time() - cur["at"] < 30):
        cur = refresh_overview(db)
    return {**cur, "database": db}


@app.get("/api/tables")
def tables(db: str | None = None, ds: int = 1, order: str = "space", page: int = 0, fresh: bool = False):
    db = safe_db(db)
    ds = int(ds) if 0 < int(ds) < 100000 else 1
    order = order if order in ORDER_COL else "space"
    page = max(0, int(page))
    key = (db, ds, order, page)
    now = time.time()
    c = _tb.get(key)
    if not fresh and c and now - c["at"] < 60:
        return {**c["payload"], "from_cache": True, "at": c["at"]}
    try:
        rows = query(sql_tables(db, ds, order, page * PAGE))
    except Exception as e:
        return {"rows": [], "error": str(e), "from_cache": False, "at": now,
                "database": db, "ds": ds, "order": order, "page": page, "has_next": False}
    has_next = len(rows) > PAGE
    rows = rows[:PAGE]
    norm = [{"db": r.get("dbname"), "schema": r.get("schema"), "table": r.get("tablename"),
             "owner": r.get("owner"), "objid": int(r.get("objid") or 0),
             "distribute_on": (r.get("distribute_on") or "RANDOM").strip().strip(",").strip() or "RANDOM",
             "space_gb": float(r.get("gb") or 0), "skew": float(r.get("skew") or 0),
             "gb_ds": float(r.get("gb_ds") or 0)} for r in rows]
    # "Todas las bases": _V_TABLE_DIST_MAP es por-base -> 2da pasada por cada base presente (pocas)
    if db == ALL_DB and norm:
        from collections import defaultdict
        bydb = defaultdict(list)
        for n in norm:
            bydb[n["db"]].append(n["objid"])
        for dbn, ids in bydb.items():
            idlist = ",".join(str(i) for i in ids if i)
            if not idlist:
                continue
            try:
                dr = query(f"""SELECT objid, TRIM(BOTH ',' FROM
                       COALESCE(MAX(CASE WHEN distseqno=1 THEN attname END),'')||','||
                       COALESCE(MAX(CASE WHEN distseqno=2 THEN attname END),'')||','||
                       COALESCE(MAX(CASE WHEN distseqno=3 THEN attname END),'')) AS dist
                     FROM {dbn}.._V_TABLE_DIST_MAP WHERE objid IN ({idlist}) GROUP BY objid""")
                dmap = {int(r["objid"]): (r["dist"] or "").strip().strip(",").strip() or "RANDOM" for r in dr}
                for n in norm:
                    if n["db"] == dbn:
                        n["distribute_on"] = dmap.get(n["objid"], "RANDOM")
            except Exception:
                pass
    payload = {"rows": norm, "database": db, "ds": ds, "order": order, "page": page, "has_next": has_next}
    _tb[key] = {"payload": payload, "at": now}
    return {**payload, "from_cache": False, "at": now}


# ─── detalle de una tabla: última acción + actividad + dataslices que ocupa ───
HIST = "HISTDB_SUPPORT.ADMIN.NZ_QUERY_HISTORY"


def classify(sql: str) -> str:
    s = (sql or "").lstrip().upper()
    for kw in ("DROP", "TRUNCATE", "INSERT", "UPDATE", "DELETE", "CREATE", "GROOM", "ALTER", "SELECT"):
        if s.startswith(kw):
            return kw
    return "OTRO"


@app.get("/api/table")
def table_detail(objid: int, table: str):
    out: dict = {"objid": int(objid), "table": table}
    try:
        m = query(f"""SELECT a.database AS db, a.schema AS sch, a.owner AS owner,
                CAST(a.createdate AS DATE) AS created,
                ROUND(s.used_bytes/1073741824.0,2) AS gb, ROUND(s.skew,2) AS skew
              FROM _V_OBJ_RELATION_XDB a JOIN _V_SYS_OBJECT_STORAGE_SIZE s ON s.tblid=a.objid
              WHERE a.objid={int(objid)} LIMIT 1""")
        out["meta"] = m[0] if m else None
    except Exception as e:
        out["meta_error"] = str(e)
    tname = re.sub(r"[^A-Za-z0-9_]", "", table).upper()
    try:
        h = query(f"""SELECT QH_TEND AS tend, QH_USER AS usr, QH_DATABASE AS db, SUBSTR(QH_SQL,1,400) AS sql
              FROM {HIST}
              WHERE UPPER(QH_SQL) LIKE '%{tname}%' AND QH_USER NOT IN ('ADMIN')
              ORDER BY QH_TEND DESC LIMIT 15""")
        out["history"] = [{"tend": str(r["tend"]), "user": r["usr"], "db": r["db"],
                           "verb": classify(r["sql"]), "sql": (r["sql"] or "").strip()} for r in h]
    except Exception as e:
        out["history_error"] = str(e)
    return out


@app.get("/api/table/slices")
def table_slices(objid: int):
    try:
        rows = query(f"""SELECT dsid, ROUND(SUM(used_bytes)/1073741824.0,3) AS gb
              FROM _V_SYS_OBJECT_DSLICE_INFO WHERE tblid={int(objid)}
              GROUP BY dsid HAVING SUM(used_bytes)>0 ORDER BY gb DESC LIMIT 12""")
        return {"slices": [{"ds": int(r["dsid"]), "gb": float(r["gb"])} for r in rows]}
    except Exception as e:
        return {"slices": [], "error": str(e)}


@app.get("/manifest.webmanifest")
def manifest():
    return JSONResponse({
        "name": "nz-monitor", "short_name": "nz-monitor", "start_url": "/", "scope": "/",
        "display": "standalone", "background_color": "#0A0C10", "theme_color": "#0A0C10",
        "icons": [
            {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }, media_type="application/manifest+json")


@app.get("/sw.js")
def sw():
    return Response(
        "self.addEventListener('install',e=>self.skipWaiting());"
        "self.addEventListener('activate',e=>self.clients.claim());"
        "self.addEventListener('fetch',e=>{e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)))});",
        media_type="application/javascript")


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


HTML = r"""<!doctype html><html lang="es" data-theme="dark"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>nz-monitor</title>
<link rel="manifest" href="/manifest.webmanifest">
<meta name="theme-color" content="#0A0C10" id="tc">
<meta name="color-scheme" content="dark light">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="nz-monitor">
<link rel="apple-touch-icon" href="/static/icon-180.png">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@500;600&display=swap" rel="stylesheet">
<style>
:root, html[data-theme="dark"]{
  --font-data:"IBM Plex Mono",ui-monospace,monospace; --font-ui:"IBM Plex Sans",system-ui,sans-serif;
  --font-dense:"IBM Plex Sans Condensed",var(--font-ui);
  --bg-0:#0A0C10; --bg-1:#0F131A; --bg-2:#151A23; --line:#1F2630; --line-strong:#2B3340;
  --ink-0:#E7EAF0; --ink-1:#9BA6B4; --ink-2:#5E6878;
  --ok:#3FB950; --warn:#D8A23A; --crit:#E5484D; --info:#5BA2C9; --live:#36E0C5; --seg:#222b38; color-scheme:dark;
}
html[data-theme="light"]{
  --bg-0:#F5F7FA; --bg-1:#FFFFFF; --bg-2:#EEF1F6; --line:#E3E8EF; --line-strong:#CFD7E1;
  --ink-0:#18202C; --ink-1:#566173; --ink-2:#8A95A4;
  --ok:#1F9D3A; --warn:#B5791A; --crit:#D32F2F; --info:#2E7BA6; --live:#0AAE99; --seg:#dbe2ea; color-scheme:light;
}
*{box-sizing:border-box}
html{background:var(--bg-0);overscroll-behavior:none}
body{margin:0;min-height:100dvh;background:var(--bg-0);color:var(--ink-0);font-family:var(--font-ui);font-size:13px;
  overflow-x:hidden;overscroll-behavior:none;-webkit-text-size-adjust:100%;transition:background .2s,color .2s}
.wrap{max-width:1180px;margin:0 auto;padding:max(16px,env(safe-area-inset-top)) max(14px,env(safe-area-inset-right)) calc(40px + env(safe-area-inset-bottom)) max(14px,env(safe-area-inset-left))}
.top{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;padding-bottom:14px;border-bottom:1px solid var(--line);margin-bottom:16px}
.brand{display:flex;align-items:center;gap:11px}
.logo{width:30px;height:30px;border-radius:7px;display:grid;place-items:center;font-family:var(--font-data);font-weight:600;color:var(--bg-0);background:var(--live)}
.brand h1{font-size:15px;font-weight:600;margin:0}
.brand .sub{font-family:var(--font-dense);text-transform:uppercase;letter-spacing:.06em;font-size:10.5px;color:var(--ink-2);display:flex;align-items:center;gap:6px;margin-top:2px}
.dbsel,.osel{font-family:var(--font-data);text-transform:none;letter-spacing:0;font-size:12px;background:var(--bg-2);color:var(--info);border:1px solid var(--line-strong);border-radius:5px;padding:2px 6px;cursor:pointer;max-width:210px}
.status{display:flex;align-items:center;gap:10px}
.pill{display:inline-flex;align-items:center;gap:6px;font-family:var(--font-data);font-size:11px;padding:3px 9px;border-radius:999px}
.pill .d{width:6px;height:6px;border-radius:999px}
.pill.ok{background:color-mix(in srgb,var(--ok) 15%,transparent);color:var(--ok)} .pill.ok .d{background:var(--ok)}
.pill.crit{background:color-mix(in srgb,var(--crit) 15%,transparent);color:var(--crit)} .pill.crit .d{background:var(--crit)}
.tbtn{background:transparent;border:1px solid var(--line-strong);color:var(--ink-1);border-radius:6px;width:32px;height:30px;cursor:pointer;font-size:14px;display:grid;place-items:center}
.tbtn:hover{color:var(--live);border-color:var(--live)}
.fresh{font-family:var(--font-data);font-size:11px;color:var(--ink-2);display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin:10px 0 16px}
.dot-live{width:7px;height:7px;border-radius:999px;background:var(--live)}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:11px;transition:opacity .15s}
.kpi{background:var(--bg-1);border:1px solid var(--line);border-radius:6px;padding:13px 14px;box-shadow:inset 0 1px 0 color-mix(in srgb,#fff 5%,transparent);opacity:0;transform:translateY(6px);animation:rise .4s ease-out forwards}
.kpi .lbl{font-family:var(--font-dense);text-transform:uppercase;letter-spacing:.06em;font-size:10.5px;color:var(--ink-2)}
.kpi .val{font-family:var(--font-data);font-weight:600;font-size:27px;line-height:1.15;margin-top:6px}
.kpi .unit{font-size:11px;color:var(--ink-2);font-family:var(--font-data);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
@keyframes rise{to{opacity:1;transform:none}}
.panel{background:var(--bg-1);border:1px solid var(--line);border-radius:6px;margin-top:16px;transition:opacity .15s}
.phead{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:12px 14px;border-bottom:1px solid var(--line)}
.phead .t{font-weight:600;font-size:13.5px} .phead .s{font-size:11px;color:var(--ink-2);margin-top:2px}
.controls{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.toggle{display:flex;align-items:center;gap:7px;font-size:11px;color:var(--ink-1);cursor:pointer;font-family:var(--font-dense);text-transform:uppercase;letter-spacing:.05em}
.toggle input{accent-color:var(--live);width:15px;height:15px}
.btn{font-family:var(--font-dense);text-transform:uppercase;letter-spacing:.05em;font-size:11.5px;font-weight:600;background:transparent;color:var(--ink-0);border:1px solid var(--line-strong);padding:7px 13px;border-radius:5px;cursor:pointer}
.btn:hover{border-color:var(--live);color:var(--live)} .btn:disabled{opacity:.5}
/* heatmap de dataslices */
.dsmap{display:flex;flex-wrap:wrap;gap:3px;padding:14px}
.dscell{width:14px;height:22px;border-radius:2px;cursor:pointer;position:relative;border:1px solid transparent}
.dscell.sel{outline:2px solid var(--live);outline-offset:1px}
.dslegend{display:flex;gap:14px;padding:0 14px 12px;font-size:11px;color:var(--ink-2);font-family:var(--font-data);align-items:center;flex-wrap:wrap}
.lg{display:inline-flex;align-items:center;gap:5px}.lg i{width:10px;height:10px;border-radius:2px;display:block}
.tablescroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{width:100%;border-collapse:collapse;min-width:640px}
thead th{font-family:var(--font-dense);text-transform:uppercase;letter-spacing:.05em;font-size:10.5px;color:var(--ink-1);text-align:left;padding:9px 12px;border-bottom:1px solid var(--line-strong);position:sticky;top:0;background:var(--bg-1)}
th.r,td.r{text-align:right}
.sortable{cursor:pointer;user-select:none} .sortable:hover{color:var(--live)} .arr{color:var(--live);margin-left:3px}
tbody td{padding:8px 12px;border-bottom:1px solid color-mix(in srgb,var(--line) 60%,transparent);font-size:12.5px}
tbody tr{border-left:2px solid transparent} tbody tr:hover td{background:var(--bg-2)}
tbody tr.sev-warn{border-left-color:var(--warn)} tbody tr.sev-crit{border-left-color:var(--crit)}
.tname{font-weight:500}
.dist{font-family:var(--font-data);color:var(--ink-1);font-size:11.5px} .dist.random{color:var(--warn)}
td.num{font-family:var(--font-data);font-variant-numeric:tabular-nums}
.skew{display:inline-flex;align-items:center;gap:8px;justify-content:flex-end}.skew .n{font-family:var(--font-data);font-variant-numeric:tabular-nums}
.bar{display:inline-flex;gap:2px}.bar i{width:6px;height:10px;border-radius:1px;background:var(--seg);display:block}
.bar i.on-neutral{background:var(--ink-1)} .bar i.on-warn{background:var(--warn)} .bar i.on-crit{background:var(--crit)}
.sk-neutral{color:var(--ink-1)} .sk-warn{color:var(--warn)} .sk-crit{color:var(--crit)}
@keyframes fdown{0%{background:color-mix(in srgb,var(--ok) 28%,transparent)}100%{background:transparent}}
@keyframes fup{0%{background:color-mix(in srgb,var(--crit) 28%,transparent)}100%{background:transparent}}
.flash-down{animation:fdown .7s ease-out} .flash-up{animation:fup .7s ease-out}
.tinfo{padding:9px 14px;font-family:var(--font-data);font-size:11px;color:var(--ink-2)}
.busy{opacity:.45;pointer-events:none}
.tname{cursor:pointer} .tname:hover{color:var(--live);text-decoration:underline}
.pager{display:flex;align-items:center;gap:10px;justify-content:flex-end;padding:10px 14px;border-top:1px solid var(--line);font-family:var(--font-data);font-size:11.5px;color:var(--ink-2)}
.pager #pginfo{margin-right:auto}
.pbtn{background:transparent;border:1px solid var(--line-strong);color:var(--ink-0);border-radius:5px;padding:5px 11px;cursor:pointer;font-size:12px;font-family:var(--font-dense)}
.pbtn:hover:not(:disabled){border-color:var(--live);color:var(--live)} .pbtn:disabled{opacity:.4;cursor:default}
.detail{position:fixed;inset:0;z-index:60;background:var(--bg-0);overflow:auto;padding:max(16px,env(safe-area-inset-top)) max(16px,env(safe-area-inset-right)) calc(30px+env(safe-area-inset-bottom)) max(16px,env(safe-area-inset-left))}
.detail.hidden{display:none}
.dhead{display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:14px;max-width:1180px;margin-left:auto;margin-right:auto}
.dwrap{max-width:1180px;margin:0 auto}
.dtitle{font-weight:600;font-size:16px} .dtitle small{color:var(--ink-2);font-weight:400;font-family:var(--font-data);font-size:12px;margin-left:8px}
.dmeta{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:14px}
.dmeta .c{background:var(--bg-1);border:1px solid var(--line);border-radius:6px;padding:10px 12px}
.dmeta .l{font-family:var(--font-dense);text-transform:uppercase;letter-spacing:.05em;font-size:10px;color:var(--ink-2)}
.dmeta .v{font-family:var(--font-data);font-size:15px;margin-top:3px}
.dsec{background:var(--bg-1);border:1px solid var(--line);border-radius:6px;margin-bottom:14px}
.dsec h3{font-size:12px;font-family:var(--font-dense);text-transform:uppercase;letter-spacing:.05em;color:var(--ink-1);margin:0;padding:11px 14px;border-bottom:1px solid var(--line)}
.dsec .body{padding:4px 14px 12px}
.hrow{display:flex;gap:10px;align-items:baseline;padding:7px 0;border-bottom:1px solid color-mix(in srgb,var(--line) 60%,transparent);font-size:12px}
.hrow .t{font-family:var(--font-data);color:var(--ink-2);white-space:nowrap;font-size:11px}
.hrow .u{font-family:var(--font-data);color:var(--ink-1);white-space:nowrap}
.vb{font-family:var(--font-data);font-size:10.5px;padding:1px 6px;border-radius:4px;white-space:nowrap}
.vb.read{background:color-mix(in srgb,var(--info) 16%,transparent);color:var(--info)}
.vb.write{background:color-mix(in srgb,var(--warn) 18%,transparent);color:var(--warn)}
.hrow .q{font-family:var(--font-data);color:var(--ink-2);font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}
.slrow{display:flex;align-items:center;gap:10px;padding:5px 0;font-family:var(--font-data);font-size:12px}
.slrow .id{width:70px;color:var(--ink-1)} .slrow .bx{flex:1;height:8px;background:var(--seg);border-radius:3px;overflow:hidden}
.slrow .bx i{display:block;height:100%;background:var(--live)} .slrow .g{width:80px;text-align:right}
.live-on .dot-live{animation:pulse 1.6s ease-in-out infinite}@keyframes pulse{0%,100%{opacity:.35}50%{opacity:1}}
@media (max-width:760px){.kpis{grid-template-columns:repeat(2,1fr)}.kpi .val{font-size:23px}.controls{width:100%}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
</style></head>
<body>
<div class="wrap">
  <div class="top">
    <div class="brand">
      <div class="logo">nz</div>
      <div><h1>nz-monitor</h1><div class="sub">Base&nbsp;<select id="dbsel" class="dbsel"><option>cargando…</option></select></div></div>
    </div>
    <div class="status">
      <span id="pill" class="pill ok"><span class="d"></span><span id="pilltxt">conectado</span></span>
      <button class="tbtn" id="theme" title="Cambiar tema">◐</button>
    </div>
  </div>

  <div class="kpis" id="kpis">
    <div class="kpi" style="animation-delay:0ms"><div class="lbl">Espacio usado</div><div class="val" id="k-space">—</div><div class="unit">GB en esta base</div></div>
    <div class="kpi" style="animation-delay:40ms"><div class="lbl">Total de tablas</div><div class="val" id="k-count">—</div><div class="unit">en la base</div></div>
    <div class="kpi" style="animation-delay:80ms"><div class="lbl">Peor skew</div><div class="val" id="k-skew">—</div><div class="unit">más mal distribuida</div></div>
    <div class="kpi" style="animation-delay:120ms"><div class="lbl">Dataslice más lleno</div><div class="val" id="k-ds">—</div><div class="unit" id="k-dsname">del clúster</div></div>
  </div>
  <div class="fresh" id="freshbox"><span class="dot-live"></span><span id="fresh">—</span><span style="color:var(--ink-2)">· se actualiza solo, sin recargar</span></div>

  <div class="panel">
    <div class="phead">
      <div><div class="t">Uso de dataslices (clúster)</div><div class="s">Cada celda = un dataslice. Rojo ≥95% · ámbar ≥85%. Toca uno para ver qué tablas lo cargan.</div></div>
    </div>
    <div class="dsmap" id="dsmap"><span style="color:var(--ink-2);padding:8px">cargando…</span></div>
    <div class="dslegend">
      <span class="lg"><i style="background:var(--crit)"></i> ≥95%</span>
      <span class="lg"><i style="background:var(--warn)"></i> ≥85%</span>
      <span class="lg"><i style="background:var(--ok)"></i> &lt;85%</span>
      <span id="dssel" style="margin-left:auto;color:var(--live)"></span>
    </div>
  </div>

  <div class="panel" id="panel">
    <div class="phead">
      <div>
        <div class="t">Tablas: tamaño, distribución y carga por dataslice</div>
        <div class="s">Rojo / ámbar = skew alto (mal distribuida). “GB en DS” = cuánto pone la tabla en el dataslice elegido.</div>
      </div>
      <div class="controls">
        <select id="osel" class="osel" title="Ordenar por">
          <option value="space">Ordenar: Espacio</option>
          <option value="skew">Ordenar: Mala distribución</option>
          <option value="ds">Ordenar: Carga en dataslice</option>
        </select>
        <label class="toggle"><input type="checkbox" id="live"> auto</label>
        <button class="btn" id="refresh">Actualizar</button>
      </div>
    </div>
    <div class="tablescroll">
      <table>
        <thead><tr>
          <th>Base</th><th>Esquema</th><th>Tabla</th><th>Owner</th><th>Distribuida por</th>
          <th class="r sortable" data-o="space">Tamaño GB<span class="arr"></span></th>
          <th class="r sortable" data-o="ds"><span id="th-ds-lbl">GB en DS</span><span class="arr"></span></th>
          <th class="r sortable" data-o="skew">Skew %<span class="arr"></span></th>
        </tr></thead>
        <tbody id="rows"><tr><td colspan="8" style="text-align:center;color:var(--ink-2);padding:26px">cargando…</td></tr></tbody>
      </table>
    </div>
    <div class="tinfo" id="tinfo">—</div>
    <div class="pager">
      <span id="pginfo"></span>
      <button class="pbtn" id="prev" disabled>‹ Anterior</button>
      <button class="pbtn" id="next" disabled>Siguiente ›</button>
    </div>
  </div>
</div>

<div id="detail" class="detail hidden">
  <div class="dhead"><button class="pbtn" id="dback">← Volver al dashboard</button><span class="dtitle" id="dtitle"></span></div>
  <div class="dwrap">
    <div class="dmeta" id="dmeta"></div>
    <div class="dsec"><h3>Última acción y actividad reciente</h3><div class="body" id="dhist">cargando…</div></div>
    <div class="dsec"><h3>Dataslices que ocupa (top por GB)</h3><div class="body" id="dslices">cargando…</div></div>
  </div>
</div>

<script>
const $=id=>document.getElementById(id);
let lastCollected=0, prev={}, curDs=1, firstDs=true, curPage=0, hasNext=false;
const curDb=()=>$('dbsel').value, curOrder=()=>$('osel').value;

function applyTheme(t){document.documentElement.dataset.theme=t;$('tc').setAttribute('content',t==='light'?'#F5F7FA':'#0A0C10');$('theme').textContent=t==='light'?'☀':'◐';}
let theme=localStorage.getItem('theme')||(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark');applyTheme(theme);
$('theme').onclick=()=>{theme=theme==='light'?'dark':'light';localStorage.setItem('theme',theme);applyTheme(theme);};
function ago(ts){if(!ts)return "—";const s=Math.max(0,Math.round(Date.now()/1000-ts));return "actualizado hace "+s+" s";}
setInterval(()=>{$('fresh').textContent=ago(lastCollected);},1000);

function tier(s){return s>=25?'crit':s>=8?'warn':'neutral';}
function bar(s){let n=s>=100?4:s>=25?3:s>=8?2:1,t=tier(s),h='';for(let i=0;i<4;i++)h+=`<i class="${i<n?'on-'+t:''}"></i>`;return `<span class="bar">${h}</span>`;}
function dsColor(p){return p>=95?'var(--crit)':p>=85?'var(--warn)':'var(--ok)';}

function renderDataslices(j){
  const rows=j.rows||[]; if(!rows.length){$('dsmap').innerHTML='<span style="color:var(--ink-2);padding:8px">sin datos</span>';return;}
  if(firstDs){const full=rows.reduce((a,b)=>b.pct>a.pct?b:a,rows[0]);curDs=full.id;firstDs=false;}
  let full=rows.reduce((a,b)=>b.pct>a.pct?b:a,rows[0]);
  $('k-ds').textContent=full.pct.toFixed(1)+'%';$('k-dsname').textContent='DS '+full.id+' · '+full.gb_used+'/'+full.gb_size+' GB';
  $('dsmap').innerHTML=rows.map(d=>`<div class="dscell ${d.id===curDs?'sel':''}" title="DS ${d.id} · ${d.pct}% · ${d.gb_used} GB" data-id="${d.id}" style="background:${dsColor(d.pct)}"></div>`).join('');
  $('dssel').textContent='Dataslice elegido: DS '+curDs;
  $('th-ds-lbl').textContent='GB en DS'+curDs;
  document.querySelectorAll('.dscell').forEach(c=>c.onclick=()=>{
    curDs=+c.dataset.id;
    document.querySelectorAll('.dscell.sel').forEach(e=>e.classList.remove('sel'));  // resalte INSTANTANEO
    c.classList.add('sel');
    $('dssel').textContent='Dataslice elegido: DS '+curDs;
    $('th-ds-lbl').textContent='GB en DS'+curDs;
    $('osel').value='ds'; curPage=0;
    reloadAll(true);
  });
}
function renderOverview(j){
  const ok=j.status==='ok';$('pill').className='pill '+(ok?'ok':'crit');$('pilltxt').textContent=ok?'conectado':'sin acceso';
  if(j.data){$('k-space').textContent=j.data.total_gb.toLocaleString();$('k-count').textContent=j.data.table_count.toLocaleString();lastCollected=j.at;$('fresh').textContent=ago(lastCollected);}
  else{$('k-space').textContent='—';$('k-count').textContent='—';}
}
function setArrows(order){document.querySelectorAll('th.sortable').forEach(th=>{th.querySelector('.arr').textContent=(th.dataset.o===order)?'▾':'';});}
function renderTables(j){
  $('th-ds-lbl').textContent='GB en DS'+(j.ds||curDs); setArrows(j.order||curOrder());
  curPage=j.page||0; hasNext=!!j.has_next;
  $('pginfo').textContent='Página '+(curPage+1); $('prev').disabled=curPage<=0; $('next').disabled=!hasNext;
  if(j.error){$('rows').innerHTML=`<tr><td colspan=8 style="text-align:center;color:var(--crit);padding:26px">sin acceso a esta base</td></tr>`;$('tinfo').textContent=(j.error||'').slice(0,90);$('k-skew').textContent='—';return;}
  let maxSkew=0,html='';
  for(const x of j.rows){
    if(x.skew>maxSkew)maxSkew=x.skew;
    const t=tier(x.skew),key=(x.db||'')+'.'+x.schema+'.'+x.table,p=prev[key];let fS='',fK='',fD='';
    if(p){if(x.space_gb<p.space_gb)fS='flash-down';else if(x.space_gb>p.space_gb)fS='flash-up';
          if(x.skew<p.skew)fK='flash-down';else if(x.skew>p.skew)fK='flash-up';
          if(x.gb_ds<p.gb_ds)fD='flash-down';else if(x.gb_ds>p.gb_ds)fD='flash-up';}
    prev[key]={space_gb:x.space_gb,skew:x.skew,gb_ds:x.gb_ds};
    const dist=x.distribute_on==='RANDOM'?'<span class="dist random">RANDOM</span>':(x.distribute_on==='—'?'<span class="dist">—</span>':`<span class="dist">${x.distribute_on}</span>`);
    html+=`<tr class="sev-${t}"><td style="color:var(--ink-2)">${x.db||''}</td><td style="color:var(--ink-1)">${x.schema||''}</td>
      <td class="tname" data-objid="${x.objid}" data-table="${(x.table||'').replace(/"/g,'&quot;')}">${x.table||''}</td><td style="color:var(--ink-1)">${x.owner||''}</td>
      <td>${dist}</td><td class="num r ${fS}">${x.space_gb.toLocaleString()}</td>
      <td class="num r ${fD}">${x.gb_ds.toLocaleString()}</td>
      <td class="num r ${fK}"><span class="skew"><span class="n sk-${t}">${x.skew.toFixed(2)}</span>${bar(x.skew)}</span></td></tr>`;
  }
  $('rows').innerHTML=html||'<tr><td colspan=8 style="text-align:center;color:var(--ink-2);padding:26px">sin tablas</td></tr>';
  const omap={space:'espacio',skew:'mala distribución',ds:'carga en DS'+j.ds};
  $('tinfo').textContent=`${j.rows.length} tablas · orden: ${omap[j.order]||j.order} · ${j.from_cache?'datos recientes':'datos en vivo'} · ${new Date(j.at*1000).toLocaleTimeString()}`;
  $('k-skew').innerHTML=`<span class="sk-${tier(maxSkew)}">${maxSkew.toFixed(2)}</span>`;
}
function setBusy(on){$('kpis').classList.toggle('busy',on);$('panel').classList.toggle('busy',on);const b=$('refresh');b.disabled=on;b.textContent=on?'Consultando…':'Actualizar';}

async function reloadAll(fresh,dim=true){
  if(dim)setBusy(true);
  try{
    const tq='/api/tables?db='+encodeURIComponent(curDb())+'&ds='+curDs+'&order='+curOrder()+'&page='+curPage+(fresh?'&fresh=true':'');
    const [ov,tb,ds]=await Promise.all([
      fetch('/api/overview?db='+encodeURIComponent(curDb())).then(r=>r.json()),
      fetch(tq).then(r=>r.json()),
      fetch('/api/dataslices').then(r=>r.json()),
    ]);
    renderDataslices(ds); renderOverview(ov); renderTables(tb);
  }catch(e){}finally{if(dim)setBusy(false);}
}

async function loadDatabases(){
  const j=await (await fetch('/api/databases')).json();const sel=$('dbsel');sel.innerHTML='';
  const all=document.createElement('option');all.value='*';all.textContent='Todas las bases';sel.appendChild(all);
  for(const d of j.databases){const o=document.createElement('option');o.value=d;o.textContent=d;if(d===j.default)o.selected=true;sel.appendChild(o);}
  sel.onchange=()=>{prev={};lastCollected=0;curPage=0;reloadAll(true);};
}
$('osel').onchange=()=>{curPage=0;reloadAll(true);};
document.querySelectorAll('th.sortable').forEach(th=>th.onclick=()=>{$('osel').value=th.dataset.o;curPage=0;reloadAll(true);});
$('refresh').onclick=()=>reloadAll(true);

// paginación (solo recarga la tabla, no KPIs/dataslices)
async function loadTablesPage(){setBusy(true);try{
  const tq='/api/tables?db='+encodeURIComponent(curDb())+'&ds='+curDs+'&order='+curOrder()+'&page='+curPage+'&fresh=true';
  renderTables(await (await fetch(tq)).json());
}catch(e){}finally{setBusy(false);}}
$('prev').onclick=()=>{if(curPage>0){curPage--;loadTablesPage();}};
$('next').onclick=()=>{if(hasNext){curPage++;loadTablesPage();}};

// vista de detalle de tabla
function vbcls(v){return v==='SELECT'?'read':(v==='OTRO'?'':'write');}
async function openDetail(objid,table){
  $('detail').classList.remove('hidden');document.body.style.overflow='hidden';window.scrollTo(0,0);
  $('dtitle').innerHTML=table+' <small>cargando…</small>';$('dmeta').innerHTML='';$('dhist').textContent='cargando…';$('dslices').textContent='cargando…';
  try{
    const j=await (await fetch('/api/table?objid='+encodeURIComponent(objid)+'&table='+encodeURIComponent(table))).json();
    const m=j.meta||{};
    $('dtitle').innerHTML=table+` <small>${m.db||''}.${m.sch||''} · ${m.owner||''}</small>`;
    const skcls=m.skew>=25?'sk-crit':m.skew>=8?'sk-warn':'sk-neutral';
    $('dmeta').innerHTML=`<div class="c"><div class="l">Tamaño</div><div class="v">${m.gb??'—'} GB</div></div>
      <div class="c"><div class="l">Skew</div><div class="v ${skcls}">${m.skew??'—'}</div></div>
      <div class="c"><div class="l">Creada</div><div class="v">${m.created||'—'}</div></div>
      <div class="c"><div class="l">Base · Esquema</div><div class="v">${m.db||''}.${m.sch||''}</div></div>`;
    const h=j.history||[];
    $('dhist').innerHTML = h.length? h.map(r=>`<div class="hrow"><span class="t">${(r.tend||'').slice(0,19)}</span><span class="vb ${vbcls(r.verb)}">${r.verb}</span><span class="u">${r.user||''}</span><span class="q">${(r.sql||'').replace(/</g,'&lt;').slice(0,160)}</span></div>`).join('')
      : '<div style="color:var(--ink-2);padding:8px 0">Sin actividad en el historial reciente.</div>';
  }catch(e){$('dhist').textContent='error al cargar';}
  try{
    const s=await (await fetch('/api/table/slices?objid='+encodeURIComponent(objid))).json();
    const sl=s.slices||[];const mx=sl.length?Math.max(...sl.map(x=>x.gb)):1;
    $('dslices').innerHTML = sl.length? sl.map(x=>`<div class="slrow"><span class="id">DS ${x.ds}</span><span class="bx"><i style="width:${Math.max(3,x.gb/mx*100)}%"></i></span><span class="g">${x.gb} GB</span></div>`).join('')
      : '<div style="color:var(--ink-2);padding:8px 0">Sin datos de dataslices.</div>';
  }catch(e){$('dslices').textContent='error al cargar';}
}
$('dback').onclick=()=>{$('detail').classList.add('hidden');document.body.style.overflow='';};
$('rows').addEventListener('click',e=>{const td=e.target.closest('.tname');if(td&&td.dataset.objid)openDetail(td.dataset.objid,td.dataset.table);});
let liveTimer=null;
$('live').onchange=e=>{document.body.classList.toggle('live-on',e.target.checked);if(e.target.checked){liveTimer=setInterval(()=>reloadAll(true,false),20000);}else{clearInterval(liveTimer);}};
(async()=>{await loadDatabases();
  // primero dataslices para fijar el DS más lleno como objetivo, luego todo junto
  const ds=await (await fetch('/api/dataslices')).json();renderDataslices(ds);
  await reloadAll(false);
  setInterval(()=>{fetch('/api/overview?db='+encodeURIComponent(curDb())).then(r=>r.json()).then(renderOverview);},10000);
})();
if('serviceWorker' in navigator){navigator.serviceWorker.register('/sw.js').catch(()=>{});}
</script>
</body></html>
"""
