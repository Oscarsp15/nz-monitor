"""Conexión a Netezza con nzpy (conector 100% Python, oficial de IBM) + pool.

Por qué nzpy y no ODBC/JDBC:
  - Es Python puro: habla el protocolo de Netezza por TCP, sin Java ni driver ODBC.
  - Instalar = `pip install nzpy`. Multiplataforma y trivial de compartir.
  - DB-API 2.0 (cursor/execute/fetchall), igual que sqlite3/psycopg.

Pool simple por host:port:db:user, reutilizable, con timeout de query.
"""

import os
import threading
from contextlib import contextmanager

import nzpy

# securityLevel: 0=preferUnsecured, 1=preferSecured, 2=requireUnsecured, 3=requireSecured
SECURITY_LEVEL = int(os.getenv("NETEZZA_SECURITY_LEVEL", "0"))
QUERY_TIMEOUT = int(os.getenv("NETEZZA_QUERY_TIMEOUT", "30"))
_POOL_MAX = int(os.getenv("NETEZZA_POOL_MAX_SIZE", "5"))

_pools: dict[str, list] = {}
_pool_lock = threading.Lock()


def _key(host: str, port: int, database: str, user: str) -> str:
    return f"{host}:{port}:{database}:{user}"


def _new_connection(host: str, port: int, database: str, user: str, password: str):
    return nzpy.connect(
        user=user,
        password=password,
        host=host,
        port=port,
        database=database,
        securityLevel=SECURITY_LEVEL,
    )


@contextmanager
def get_connection(host: str, port: int, database: str, user: str, password: str):
    """Toma una conexión del pool (o crea una) y la devuelve al terminar."""
    k = _key(host, port, database, user)
    conn = None
    with _pool_lock:
        pool = _pools.setdefault(k, [])
        if pool:
            conn = pool.pop()
    if conn is None:
        conn = _new_connection(host, port, database, user, password)
    try:
        yield conn
        with _pool_lock:  # devolver al pool si hay espacio
            pool = _pools.setdefault(k, [])
            if len(pool) < _POOL_MAX:
                pool.append(conn)
                conn = None
    finally:
        if conn is not None:  # pool lleno o hubo error → cerrar
            try:
                conn.close()
            except Exception:
                pass


def execute_query(
    host: str, port: int, database: str, user: str, password: str,
    sql: str, params: tuple | None = None,
) -> list[dict]:
    """Ejecuta una query y devuelve filas como lista de dicts."""
    with get_connection(host, port, database, user, password) as conn:
        cur = conn.cursor()
        try:
            try:
                cur.execute(f"SET QUERY_TIMEOUT {QUERY_TIMEOUT}")  # límite del lado Netezza
            except Exception:
                pass
            cur.execute(sql, params or ())
            if cur.description is None:
                return []
            cols = [d[0].lower() for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            cur.close()


def test_connection(host: str, port: int, database: str, user: str, password: str) -> dict:
    try:
        rows = execute_query(host, port, database, user, password, "SELECT CURRENT_TIMESTAMP")
        return {"status": "connected", "host": host, "database": database,
                "timestamp": str(rows[0]) if rows else None}
    except Exception as e:
        return {"status": "error", "host": host, "database": database, "error": str(e)}
