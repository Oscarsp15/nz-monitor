"""SQL de observabilidad de Netezza — queries PROBADAS (ver ../../NETEZZA.md).

Las entradas se validan en el service (db contra catálogo, ds/page enteros, order de lista
blanca) antes de formatear, para evitar inyección.
"""

ORDER_COL = {"space": "gb", "skew": "skew"}
PAGE = 25
HIST = "HISTDB_SUPPORT.ADMIN.NZ_QUERY_HISTORY"

SQL_DATABASES = "SELECT DATABASE FROM _V_DATABASE ORDER BY DATABASE"

SQL_DSLICE = ("SELECT ds_id, ds_percentused AS pct, ROUND(ds_used/1073741824.0,1) AS gb_used, "
              "ds_size AS gb_size, ds_status FROM _V_DSLICE ORDER BY ds_id")

# Espacio + nº de tablas por base (todas las bases) — query pesada → solo en el recolector.
SQL_SPACE_BY_DB = (
    "SELECT a.database AS dbname, COUNT(*) AS table_count, "
    "ROUND(SUM(s.used_bytes)/1073741824.0,2) AS gb "
    "FROM _V_OBJ_RELATION_XDB a JOIN _V_SYS_OBJECT_STORAGE_SIZE s ON s.tblid=a.objid "
    "WHERE a.OBJTYPE='TABLE' GROUP BY a.database ORDER BY gb DESC NULLS LAST"
)


def _where_db(db: str | None) -> str:
    return "" if not db else f" AND a.database='{db}'"


def overview(db: str | None) -> str:
    return (f"SELECT COUNT(*) AS table_count, "
            f"ROUND(COALESCE(SUM(s.used_bytes),0)/1073741824.0,2) AS total_gb "
            f"FROM _V_OBJ_RELATION_XDB a JOIN _V_SYS_OBJECT_STORAGE_SIZE s ON s.tblid=a.objid "
            f"WHERE a.OBJTYPE='TABLE'{_where_db(db)}")


def owners(db: str | None) -> str:
    return (f"SELECT a.owner AS owner, COUNT(*) AS tablas, "
            f"ROUND(SUM(s.used_bytes)/1073741824.0,2) AS gb "
            f"FROM _V_OBJ_RELATION_XDB a JOIN _V_SYS_OBJECT_STORAGE_SIZE s ON s.tblid=a.objid "
            f"WHERE a.OBJTYPE='TABLE'{_where_db(db)} GROUP BY a.owner ORDER BY gb DESC NULLS LAST")


def _search_clause(search: str | None) -> str:
    # `search` ya viene saneado en el service (solo [A-Z0-9_ ]) → seguro para LIKE.
    if not search:
        return ""
    return f" AND (UPPER(a.objname) LIKE '%{search}%' OR UPPER(a.owner) LIKE '%{search}%')"


def tables(db: str | None, order: str, offset: int, search: str | None = None) -> str:
    # `skew` = (máx − promedio)/promedio de bytes sobre todos los dataslices (validado vs Netezza):
    # 0=balanceada, 45=un dataslice con 45× el promedio, ~Ndataslices=toda en uno. Ver NETEZZA.md.
    oc = ORDER_COL.get(order, "gb")
    if not db:  # todas las bases: _V_TABLE_DIST_MAP es por-base -> sin join (2ª pasada en service)
        dist_sel, dist_join = "'—'", ""
    else:
        dist_sel = "COALESCE(dm.dist,'RANDOM')"
        dist_join = (f"LEFT JOIN (SELECT objid, {dist_expr()} AS dist "
                     f"FROM {db}.._V_TABLE_DIST_MAP GROUP BY objid) dm ON dm.objid=a.objid")
    return f"""
      SELECT a.database AS dbname, a.schema AS schema, a.objname AS tablename, a.owner AS owner, a.objid AS objid,
        ROUND(s.used_bytes/1073741824.0,2) AS gb,
        ROUND(s.skew,2) AS skew,
        {dist_sel} AS distribute_on
      FROM _V_OBJ_RELATION_XDB a
      JOIN _V_SYS_OBJECT_STORAGE_SIZE s ON s.tblid=a.objid
      {dist_join}
      WHERE a.OBJTYPE='TABLE'{_where_db(db)}{_search_clause(search)}
      ORDER BY {oc} DESC NULLS LAST LIMIT {PAGE + 1} OFFSET {offset}
    """


def dist_expr() -> str:
    return ("TRIM(BOTH ',' FROM "
            "COALESCE(MAX(CASE WHEN distseqno=1 THEN attname END),'')||','||"
            "COALESCE(MAX(CASE WHEN distseqno=2 THEN attname END),'')||','||"
            "COALESCE(MAX(CASE WHEN distseqno=3 THEN attname END),''))")


def dist_for_ids(db: str, idlist: str) -> str:
    return (f"SELECT objid, {dist_expr()} AS dist FROM {db}.._V_TABLE_DIST_MAP "
            f"WHERE objid IN ({idlist}) GROUP BY objid")


def table_meta(objid: int) -> str:
    return (f"SELECT a.database AS db, a.schema AS sch, a.owner AS owner, "
            f"CAST(a.createdate AS DATE) AS created, "
            f"ROUND(s.used_bytes/1073741824.0,2) AS gb, ROUND(s.skew,2) AS skew "
            f"FROM _V_OBJ_RELATION_XDB a JOIN _V_SYS_OBJECT_STORAGE_SIZE s ON s.tblid=a.objid "
            f"WHERE a.objid={objid} LIMIT 1")


def table_slices(objid: int) -> str:
    return (f"SELECT dsid, ROUND(SUM(used_bytes)/1073741824.0,3) AS gb "
            f"FROM _V_SYS_OBJECT_DSLICE_INFO WHERE tblid={objid} "
            f"GROUP BY dsid HAVING SUM(used_bytes)>0 ORDER BY gb DESC LIMIT 12")


def table_history(tname_safe: str) -> str:
    return (f"SELECT QH_TEND AS tend, QH_USER AS usr, QH_DATABASE AS db, SUBSTR(QH_SQL,1,400) AS sql "
            f"FROM {HIST} WHERE UPPER(QH_SQL) LIKE '%{tname_safe}%' AND QH_USER NOT IN ('ADMIN') "
            f"ORDER BY QH_TEND DESC LIMIT 15")
