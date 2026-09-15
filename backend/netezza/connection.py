"""Conexión a Netezza con nzpy (conector 100% Python, oficial de IBM) + pool.

Por qué nzpy y no ODBC/JDBC:
  - Es Python puro: habla el protocolo de Netezza por TCP, sin Java ni driver ODBC.
  - Instalar = `pip install nzpy`. Multiplataforma y trivial de compartir.
  - DB-API 2.0 (cursor/execute/fetchall), igual que sqlite3/psycopg.

Pool simple por host:port:db:user, reutilizable, con timeout de conexión Y de query
(`netezza_connect_timeout` / `netezza_query_timeout`, ver ARCHITECTURE §5).
"""

import threading
from contextlib import contextmanager, suppress

import nzpy

from config import get_settings

# margen sobre el timeout de query para el socket: el límite real lo pone Netezza
# (`SET QUERY_TIMEOUT`); el del socket solo existe para que una VPN que se cae a mitad de
# consulta no deje el request colgado para siempre.
_SOCKET_MARGIN = 5

_pools: dict[str, list] = {}
_pool_lock = threading.Lock()


def _key(host: str, port: int, database: str, user: str) -> str:
    return f"{host}:{port}:{database}:{user}"


def _new_connection(host: str, port: int, database: str, user: str, password: str):
    """Abre una conexión con timeout de conexión (`netezza_connect_timeout`, 10 s por defecto).

    Sin él, con la VPN caída el `connect()` se quedaba a merced del timeout de TCP del sistema
    (minutos) y el request colgado. `nzpy` aplica ese `timeout` al socket y lo DEJA puesto toda la
    sesión, así que después de conectar se sube al del query + margen: si no, una consulta de
    catálogo legítima de 5 s moriría contra un socket de 10 s… y una de 40 s también, pero eso ya
    lo corta Netezza con `SET QUERY_TIMEOUT`.
    """
    s = get_settings()
    conn = nzpy.connect(
        user=user,
        password=password,
        host=host,
        port=port,
        database=database,
        # securityLevel: 0=preferUnsecured, 1=preferSecured, 2=requireUnsecured, 3=requireSecured
        securityLevel=s.netezza_security_level,
        timeout=s.netezza_connect_timeout,
    )
    sock = getattr(conn, "_usock", None)
    if sock is not None:
        with suppress(OSError):
            sock.settimeout(s.netezza_query_timeout + _SOCKET_MARGIN)
    return conn


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
            if len(pool) < get_settings().netezza_pool_max_size:
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
                # límite del lado Netezza (el del socket, en _new_connection, es la red)
                cur.execute(f"SET QUERY_TIMEOUT {get_settings().netezza_query_timeout}")
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
