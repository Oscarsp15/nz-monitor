"""Auth: login obligatorio con JWT y roles (viewer < operador < admin). Ver deps.py / router.py."""
from .bootstrap import bootstrap_users
from .deps import (
    CurrentUser,
    deny_live_for_viewer,
    deny_password_pending,
    deny_password_pending_stream,
    optional_user,
    require_auth,
    require_auth_stream,
    require_role,
)
from .roles import Role, role_at_least
from .router import router

__all__ = [
    "CurrentUser", "Role", "bootstrap_users", "deny_live_for_viewer",
    "deny_password_pending", "deny_password_pending_stream",
    "optional_user", "require_auth", "require_auth_stream", "require_role", "role_at_least",
    "router",
]
