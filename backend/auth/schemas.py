"""Tipos de validación de credenciales, compartidos por `auth/` y `users/` (Pydantic v2)."""
from typing import Annotated

from pydantic import StringConstraints

# usuario: mínimo 3 caracteres y sin espacios
Username = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=64, pattern=r"^\S+$"),
]

# contraseña: mínimo 8 caracteres
Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]
