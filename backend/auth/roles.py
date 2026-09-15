"""Jerarquía de roles: viewer < operador < admin (ver CONTRATO / AGENTS §9)."""
from typing import Literal

Role = Literal["admin", "operador", "viewer"]

# nivel numérico para comparar "al menos este rol"
ROLE_LEVEL: dict[str, int] = {"viewer": 1, "operador": 2, "admin": 3}

ROLE_LABEL: dict[str, str] = {
    "viewer": "consulta",
    "operador": "operador",
    "admin": "administrador",
}


def role_at_least(role: str, minimum: str) -> bool:
    """¿`role` tiene al menos el nivel de `minimum`? Rol desconocido → False (deniega)."""
    return ROLE_LEVEL.get(role, 0) >= ROLE_LEVEL[minimum]
