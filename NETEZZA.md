# NETEZZA.md — vistas y queries probadas

Conocimiento validado **contra el Netezza real** (Release 11.2.1.11) durante el prototipo.
Todas estas queries funcionan vía **nzpy**. Reusar en el producto.

## Conector
`nzpy` (Python puro): `nzpy.connect(user, password, host, port=5480, database, securityLevel=0)`.
DB-API 2.0. **Sin ODBC ni Java.**

## Vistas clave

| Vista | Qué da | Ámbito |
|---|---|---|
| `_V_DATABASE` | lista de bases (`DATABASE`) | catálogo actual |
| `_V_OBJ_RELATION_XDB` | catálogo **CROSS-DB**: `objid, database, schema, objname, owner, createdate, OBJTYPE` | **todas las bases** |
| `_V_SYS_OBJECT_STORAGE_SIZE` | por tabla: `tblid, used_bytes, skew` | **cross-DB** |
| `_V_SYS_OBJECT_DSLICE_INFO` | por tabla **POR dataslice**: `tblid, dsid, used_bytes` | **cross-DB** |
| `_V_DSLICE` | uso por dataslice: `ds_id, ds_percentused, ds_used, ds_size, ds_status` | clúster |
| `_V_TABLE_DIST_MAP` | columnas de distribución: `objid, distseqno, attname` | **POR-BASE** (usar `{db}.._V_TABLE_DIST_MAP`) |
| `_V_TABLE_STORAGE_STAT` | per-tabla rico: `used_max/min/spread, skew, dslicecount, allocated_bytes` | catálogo actual |
| `HISTDB_SUPPORT.ADMIN.NZ_QUERY_HISTORY` | historial: `QH_TEND, QH_USER, QH_DATABASE, QH_SQL` | global |

> **Clave del proyecto:** `_V_OBJ_RELATION_XDB` + `_V_SYS_OBJECT_*` son **globales** → una sola conexión
> sirve para consultar cualquier base (no hay que reconectar por base). Las `_V_*` "normales"
> (storage_stat, dist_map) son del **catálogo actual** y se referencian cross-db con `{db}..vista`.

## Queries probadas

### Resumen por base (espacio + nº tablas)
```sql
SELECT COUNT(*) AS table_count, ROUND(COALESCE(SUM(s.used_bytes),0)/1073741824.0,2) AS total_gb
FROM _V_OBJ_RELATION_XDB a JOIN _V_SYS_OBJECT_STORAGE_SIZE s ON s.tblid=a.objid
WHERE a.OBJTYPE='TABLE' AND a.database='{DB}';   -- omitir el AND para TODAS las bases
```

### Tablas: tamaño + skew + distribución + carga en un dataslice
```sql
SELECT a.database, a.schema, a.objname, a.owner, a.objid,
  ROUND(s.used_bytes/1073741824.0,2) AS gb,
  ROUND(s.skew,2) AS skew,
  ROUND(COALESCE(dsx.bytes_ds,0)/1073741824.0,2) AS gb_ds,
  COALESCE(dm.dist,'RANDOM') AS distribute_on
FROM _V_OBJ_RELATION_XDB a
JOIN _V_SYS_OBJECT_STORAGE_SIZE s ON s.tblid=a.objid
LEFT JOIN (SELECT tblid, SUM(used_bytes) AS bytes_ds
           FROM _V_SYS_OBJECT_DSLICE_INFO WHERE dsid={DS} GROUP BY tblid) dsx ON dsx.tblid=a.objid
LEFT JOIN (SELECT objid, TRIM(BOTH ',' FROM
             COALESCE(MAX(CASE WHEN distseqno=1 THEN attname END),'')||','||
             COALESCE(MAX(CASE WHEN distseqno=2 THEN attname END),'')||','||
             COALESCE(MAX(CASE WHEN distseqno=3 THEN attname END),'')) AS dist
           FROM {DB}.._V_TABLE_DIST_MAP GROUP BY objid) dm ON dm.objid=a.objid
WHERE a.OBJTYPE='TABLE' AND a.database='{DB}'
ORDER BY gb DESC NULLS LAST LIMIT 25 OFFSET {OFFSET};   -- order: gb | skew | gb_ds
```

### Uso por dataslice (clúster)
```sql
SELECT ds_id, ds_percentused, ROUND(ds_used/1073741824.0,1) AS gb_used, ds_size AS gb_size, ds_status
FROM _V_DSLICE ORDER BY ds_id;
```

### Dataslices que ocupa UNA tabla (detalle)
```sql
SELECT dsid, ROUND(SUM(used_bytes)/1073741824.0,3) AS gb
FROM _V_SYS_OBJECT_DSLICE_INFO WHERE tblid={OBJID}
GROUP BY dsid HAVING SUM(used_bytes)>0 ORDER BY gb DESC LIMIT 12;
```

### Última acción / actividad reciente de UNA tabla (on-demand)
```sql
SELECT QH_TEND, QH_USER, QH_DATABASE, SUBSTR(QH_SQL,1,400) AS sql
FROM HISTDB_SUPPORT.ADMIN.NZ_QUERY_HISTORY
WHERE UPPER(QH_SQL) LIKE '%{TABLA}%' AND QH_USER NOT IN ('ADMIN')
ORDER BY QH_TEND DESC LIMIT 15;
```
El verbo (acción) se deduce del inicio del SQL: DROP/TRUNCATE/INSERT/UPDATE/DELETE/CREATE/GROOM/ALTER/SELECT.

## ⚠️ Gotchas (aprendidos a golpes)

- **`ds_percentused` es TEXT** → `CAST(... AS FLOAT)` falla (*Cannot cast TEXT to FLOAT8*). Parsear en
  la app o `CAST AS NUMERIC(6,2)`.
- **`_V_DSLICES` (con S) NO existe** → es `_V_DSLICE`.
- **`_V_TABLE_DIST_MAP` es por-base** → en modo "todas las bases" no se puede unir cross-db en una
  query; hacer una **2ª pasada** por cada base presente en el resultado (≤25 filas → pocas queries).
- **Una conexión basta** para todas las bases gracias a las vistas `_XDB`/`_SYS_OBJECT_*`.
- **Última acción**: el historial nativo estructurado `$hist_table_access` está **congelado (2024-11)**;
  la fuente viva es el **texto** en `NZ_QUERY_HISTORY`. Para 1 tabla → `LIKE` directo (rápido). Para
  TODAS → índice invertido con `REGEXP_EXTRACT_ALL` (ver DAG, evita el `LIKE` correlacionado lento y
  descarta literales). El `LIKE` simple puede dar falsos positivos (el nombre como texto).
- **Espacio tras borrar**: `DROP` libera al instante en storage_stat; updates/deletes dentro de tablas
  necesitan **GROOM** para reclamar espacio físico.

## Referencia
DAG batch con el reporte completo (índice invertido de última acción, dataslices ocupados en JSON,
antigüedad, alerta IA por dataslice saturado): `~/airflow/dags/reporte_distribucion_tablas.py` (WSL).
