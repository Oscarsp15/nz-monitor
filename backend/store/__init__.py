"""Store local (SQLite): snapshots de métricas, ajustes cifrados y usuarios."""
from .settings_store import delete_setting, get_setting, get_sftp, set_setting, set_sftp
from .snapshots import get_db_path, init_db, latest_snapshot, save_snapshot, snapshot_history
from .users import (
    UsernameTakenError,
    count_active_admins,
    count_users,
    create_user,
    delete_user,
    get_user,
    get_user_by_username,
    init_users,
    list_users,
    touch_last_login,
    update_user,
)

__all__ = [
    "get_db_path", "init_db", "latest_snapshot", "save_snapshot", "snapshot_history",
    "get_setting", "set_setting", "delete_setting", "get_sftp", "set_sftp",
    "UsernameTakenError", "init_users", "create_user", "get_user", "get_user_by_username",
    "list_users", "count_users", "count_active_admins", "update_user", "touch_last_login",
    "delete_user",
]
