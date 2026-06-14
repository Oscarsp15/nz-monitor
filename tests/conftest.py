"""Configuración de pytest: pone backend/ en el path y aísla la BD en un archivo temporal."""
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """SQLite temporal apuntado por DATABASE_URL; recrea el singleton de settings."""
    from config import get_settings

    db = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    get_settings.cache_clear()

    import store

    store.init_db()
    yield db
    get_settings.cache_clear()
