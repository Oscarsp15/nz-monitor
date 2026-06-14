"""Login opcional: hash de contraseña (pbkdf2, stdlib) + token JWT (jose)."""
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


def make_token(user: str) -> str:
    s = get_settings()
    exp = datetime.now(UTC) + timedelta(minutes=s.jwt_expire_minutes)
    return jwt.encode({"sub": user, "exp": exp}, s.secret_key, algorithm="HS256")


def verify_token(token: str) -> str | None:
    try:
        return jwt.decode(token, get_settings().secret_key, algorithms=["HS256"]).get("sub")
    except JWTError:
        return None
