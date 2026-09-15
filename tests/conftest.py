"""Configuración de pytest: pone backend/ en el path y aísla la BD en un archivo temporal."""
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin1234"  # noqa: S105 (contraseña de prueba)
ADMIN_PASSWORD_NEW = "admin5678"  # noqa: S105 (la que estrena en las pruebas)


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """SQLite temporal apuntado por DATABASE_URL; recrea el singleton de settings."""
    from config import get_settings

    db = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("ADMIN_USER", ADMIN_USER)
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASSWORD)
    get_settings.cache_clear()

    import store

    store.init_db()
    yield db
    get_settings.cache_clear()


@pytest.fixture
def client(tmp_db) -> Iterator["object"]:
    """TestClient con lifespan (arranca la migración/siembra del admin) sobre la BD temporal."""
    from fastapi.testclient import TestClient

    import main

    with TestClient(main.app) as c:
        yield c


@pytest.fixture
def login(client) -> Callable[..., dict[str, str]]:
    """Devuelve las cabeceras `Authorization` de un usuario (por defecto, el admin sembrado)."""

    def _login(username: str = ADMIN_USER, password: str = ADMIN_PASSWORD) -> dict[str, str]:
        r = client.post("/api/auth/login", json={"username": username, "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['token']}"}

    return _login


@pytest.fixture
def admin_headers(client, login) -> dict[str, str]:
    """Admin sembrado, ya con su contraseña estrenada (sin eso la API le responde 403)."""
    headers = login()
    r = client.post("/api/auth/change-password", headers=headers,
                    json={"current_password": ADMIN_PASSWORD, "new_password": ADMIN_PASSWORD_NEW})
    assert r.status_code == 200, r.text
    return headers


@pytest.fixture
def make_user(client, admin_headers, login) -> Callable[..., dict[str, str]]:
    """Crea un usuario con el rol pedido y devuelve sus cabeceras autenticadas."""

    def _make(username: str, role: str,
              password: str = "contrasena123") -> dict[str, str]:  # noqa: S107
        r = client.post("/api/users", headers=admin_headers,
                        json={"username": username, "password": password, "role": role})
        assert r.status_code == 200, r.text
        headers = login(username, password)
        # el usuario nuevo estrena contraseña antes de poder usar la app (flujo real)
        final = password + "x"
        r = client.post("/api/auth/change-password", headers=headers,
                        json={"current_password": password, "new_password": final})
        assert r.status_code == 200, r.text
        return headers

    return _make
