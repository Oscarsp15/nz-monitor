"""Dependencias de FastAPI: autenticación obligatoria, roles y bloqueo de consultas en vivo.

El login es SIEMPRE obligatorio (ya no existe el "modo abierto" del esquema de un solo usuario).
El token se revalida contra la BD en cada request: si el usuario fue borrado o desactivado, el
token deja de servir al instante.
"""
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel

from store import get_user

from .roles import Role, role_at_least
from .security import verify_token

_UNAUTH = {"WWW-Authenticate": "Bearer"}

# parámetros que fuerzan consulta en vivo a Netezza/SFTP (ver AGENTS §2 y §8)
_LIVE_PARAMS = ("fresh", "live")
_TRUTHY = {"1", "true", "yes", "on", "si", "sí"}


class CurrentUser(BaseModel):
    """Usuario autenticado del request (nunca incluye el hash de la contraseña)."""

    id: int
    username: str
    role: Role
    must_change_password: bool


def bearer_token(authorization: str | None) -> str:
    return (authorization or "").removeprefix("Bearer ").strip()


def user_from_token(token: str) -> CurrentUser | None:
    """Valida el token y lo contrasta con la BD. None si no hay sesión utilizable."""
    claims = verify_token(token)
    if not claims:
        return None
    row = get_user(int(claims["uid"]))
    if row is None or not row["active"]:
        return None
    return CurrentUser(
        id=row["id"],
        username=row["username"],
        role=row["role"],
        must_change_password=bool(row["must_change_password"]),
    )


def optional_user(authorization: str | None = Header(None)) -> CurrentUser | None:
    """Sesión si la hay, sin fallar. Solo para `/api/auth/status`, que nunca devuelve 401."""
    return user_from_token(bearer_token(authorization))


def require_auth(authorization: str | None = Header(None)) -> CurrentUser:
    """Exige un token válido de un usuario existente y activo. Si no, 401."""
    user = user_from_token(bearer_token(authorization))
    if user is None:
        raise HTTPException(401, "No autenticado: inicia sesión de nuevo", headers=_UNAUTH)
    return user


def require_auth_stream(
    authorization: str | None = Header(None),
    token: str | None = Query(None, description="Token JWT para EventSource (SSE)"),
) -> CurrentUser:
    """Igual que `require_auth`, pero acepta `?token=` además de la cabecera.

    `EventSource` (SSE) no permite mandar cabeceras, así que `/api/stream` admite el token por
    query string. Solo ahí: en el resto de endpoints el token va en `Authorization: Bearer ...`
    para no dejarlo escrito en logs de acceso ni en el historial del navegador.
    """
    user = user_from_token(bearer_token(authorization) or (token or "").strip())
    if user is None:
        raise HTTPException(401, "No autenticado: inicia sesión de nuevo", headers=_UNAUTH)
    return user


#: usuario autenticado, listo para inyectar en un endpoint (`user: AuthUser`)
AuthUser = Annotated[CurrentUser, Depends(require_auth)]
StreamUser = Annotated[CurrentUser, Depends(require_auth_stream)]
#: sesión opcional (solo `/api/auth/status`)
MaybeUser = Annotated[CurrentUser | None, Depends(optional_user)]


def require_role(min_role: Role) -> Callable[[CurrentUser], CurrentUser]:
    """Dependencia que exige al menos `min_role` (viewer < operador < admin)."""

    def _dep(user: AuthUser) -> CurrentUser:
        if not role_at_least(user.role, min_role):
            raise HTTPException(
                403, f"Necesitas rol '{min_role}' o superior para esta acción (tu rol: "
                     f"'{user.role}')",
            )
        return user

    return _dep


def _check_password_pending(user: CurrentUser) -> CurrentUser:
    """Mientras el usuario deba cambiar su contrasena, solo puede usar `/api/auth/*`.

    La pantalla forzada del frontend es comodidad, no seguridad: sin esto, quien conoce la
    contrasena temporal (p. ej. el `admin`/`admin` inicial) podria usar la API para siempre
    sin cambiarla nunca.
    """
    if user.must_change_password:
        raise HTTPException(
            403,
            "Debes cambiar tu contrasena antes de usar la aplicacion.",
        )
    return user


def deny_password_pending(user: AuthUser) -> CurrentUser:
    return _check_password_pending(user)


def deny_password_pending_stream(user: StreamUser) -> CurrentUser:
    """Igual, para `/api/stream`: el token puede venir por `?token=` (EventSource).

    Si esta guardia dependiera de `require_auth` (solo cabecera), FastAPI resolvería esa
    dependencia por su cuenta y devolvería 401 aunque el token viajara por la query.
    """
    return _check_password_pending(user)


def deny_live_for_viewer(request: Request, user: AuthUser) -> CurrentUser:
    """Bloquea a `viewer` cualquier parámetro que fuerce consulta en vivo (`fresh`/`live`).

    Se aplica al router completo de datos, no endpoint por endpoint: así un endpoint nuevo con
    `?fresh=` queda cubierto sin acordarse de nada.
    """
    if role_at_least(user.role, "operador"):
        return user
    for param in _LIVE_PARAMS:
        value = request.query_params.get(param)
        if value is not None and value.strip().lower() in _TRUTHY:
            raise HTTPException(
                403,
                "Tu rol solo permite ver los datos ya recolectados. Para consultar Netezza en "
                "vivo (\"Actualizar ahora\" / modo en vivo) necesitas rol 'operador' o "
                "'administrador'.",
            )
    return user
