"""Timeout de CONEXIÓN a Netezza: con la VPN caída el request no puede colgarse sin límite."""
import pytest


class _FakeSock:
    def __init__(self):
        self.timeout = None

    def settimeout(self, value):
        self.timeout = value


class _FakeConn:
    def __init__(self):
        self._usock = _FakeSock()


@pytest.fixture
def fake_connect(monkeypatch):
    """Sustituye `nzpy.connect` y devuelve los kwargs con los que se le llamó."""
    import netezza.connection as conn

    seen: dict = {}

    def _connect(**kwargs):
        seen.update(kwargs)
        seen["conn"] = _FakeConn()
        return seen["conn"]

    monkeypatch.setattr(conn.nzpy, "connect", _connect)
    return seen


def test_connect_recibe_timeout(monkeypatch, fake_connect):
    import netezza.connection as conn
    from config import get_settings

    monkeypatch.setenv("SECRET_KEY", "clave-de-pruebas-no-usar-en-produccion")
    monkeypatch.setenv("NETEZZA_CONNECT_TIMEOUT", "7")
    monkeypatch.setenv("NETEZZA_QUERY_TIMEOUT", "30")
    get_settings.cache_clear()
    try:
        conn._new_connection("h", 5480, "DB", "u", "p")
    finally:
        get_settings.cache_clear()

    assert fake_connect["timeout"] == 7, "nzpy.connect debe recibir el timeout de conexión"


def test_default_del_timeout_de_conexion_es_10s():
    from config import Settings

    assert Settings(secret_key="x").netezza_connect_timeout == 10


def test_tras_conectar_el_socket_sube_al_timeout_de_query(monkeypatch, fake_connect):
    """nzpy deja el `timeout` pegado al socket toda la sesión: con 10 s moría una query de 12 s."""
    import netezza.connection as conn
    from config import get_settings

    monkeypatch.setenv("SECRET_KEY", "clave-de-pruebas-no-usar-en-produccion")
    monkeypatch.setenv("NETEZZA_CONNECT_TIMEOUT", "10")
    monkeypatch.setenv("NETEZZA_QUERY_TIMEOUT", "30")
    get_settings.cache_clear()
    try:
        c = conn._new_connection("h", 5480, "DB", "u", "p")
    finally:
        get_settings.cache_clear()

    assert c._usock.timeout == 30 + conn._SOCKET_MARGIN
