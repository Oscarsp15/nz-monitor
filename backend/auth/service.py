"""Reglas de sesión: verificar credenciales y cambiar la contraseña propia.

El router solo traduce a HTTP; aquí no se conoce FastAPI (así se prueba sin levantar la app).
"""
from store import get_user, get_user_by_username, touch_last_login, update_user

from .security import hash_password, verify_password


def authenticate(username: str, password: str) -> dict | None:
    """Devuelve la fila del usuario si las credenciales son válidas y está activo; si no, None."""
    row = get_user_by_username(username)
    if row is None or not row["active"]:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    touch_last_login(row["id"])
    return row


def change_own_password(user_id: int, current_password: str, new_password: str) -> bool:
    """Cambia la contraseña propia y limpia `must_change_password`.

    Devuelve False si la contraseña actual no coincide.
    """
    row = get_user(user_id)
    if row is None or not verify_password(current_password, row["password_hash"]):
        return False
    update_user(user_id, password_hash=hash_password(new_password), must_change_password=False)
    return True
