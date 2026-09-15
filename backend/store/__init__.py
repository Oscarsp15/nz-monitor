"""Store local (SQLite): snapshots de métricas (y a futuro auth/credenciales cifradas)."""
from .settings_store import get_setting, get_sftp, set_setting, set_sftp
from .snapshots import get_db_path, init_db, latest_snapshot, save_snapshot, snapshot_history

__all__ = [
    "get_db_path", "init_db", "latest_snapshot", "save_snapshot", "snapshot_history",
    "get_setting", "set_setting", "get_sftp", "set_sftp",
]
