"""Primitivas de auth: hash de contraseña (pbkdf2, stdlib) + token JWT (jose).

El token lleva `sub` (usuario), `uid` (id en `app_user`) y `role`, para que las dependencias
puedan decidir permisos sin pegarle a la BD... aunque igual se revalida contra la BD en cada
request (el usuario puede haber sido borrado o desactivado tras emitir el token).
"""
import base64
import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from config import get_settings

_ITER = 200_000


def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, _ITER)
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        salt_b64, dk_b64 = stored.split("$", 1)
        salt, dk = base64.b64decode(salt_b64), base64.b64decode(dk_b64)
    except (ValueError, TypeError):
        return False
    test = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, _ITER)
    return hmac.compare_digest(test, dk)


def make_token(user: str, uid: int, role: str) -> str:
    """JWT firmado con SECRET_KEY: {sub, uid, role, exp} (ver CONTRATO / ARCHITECTURE §7)."""
    s = get_settings()
    exp = datetime.now(UTC) + timedelta(minutes=s.jwt_expire_minutes)
    claims = {"sub": user, "uid": uid, "role": role, "exp": exp}
    return jwt.encode(claims, s.secret_key, algorithm="HS256")


def verify_token(token: str) -> dict | None:
    """Devuelve los claims del token, o None si es inválido/expirado/con claims incompletos."""
    try:
        claims = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
    except JWTError:
        return None
    if not claims.get("sub") or claims.get("uid") is None or not claims.get("role"):
        return None
    return claims
