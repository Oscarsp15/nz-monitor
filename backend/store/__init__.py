"""Store local (SQLite): snapshots de métricas (y a futuro auth/credenciales cifradas)."""
from .snapshots import get_db_path, init_db, latest_snapshot, save_snapshot

__all__ = ["get_db_path", "init_db", "latest_snapshot", "save_snapshot"]
