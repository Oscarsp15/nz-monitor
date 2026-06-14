"""Store local (SQLite): snapshots de métricas (y a futuro auth/credenciales cifradas)."""
from .settings_store import get_setting, get_telegram, set_setting, set_telegram
from .snapshots import get_db_path, init_db, latest_snapshot, save_snapshot, snapshot_history

__all__ = [
    "get_db_path", "init_db", "latest_snapshot", "save_snapshot", "snapshot_history",
    "get_setting", "set_setting", "get_telegram", "set_telegram",
]
