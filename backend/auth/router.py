"""Login opcional. Si no hay usuario configurado, la app queda abierta (uso en LAN)."""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from store import get_setting

from .security import make_token, verify_password, verify_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


def configured() -> bool:
    return bool(get_setting("auth_user") and get_setting("auth_pass_hash"))


def require_auth(authorization: str | None = Header(None)) -> str | None:
    """Dependencia para proteger endpoints. Sin login configurado → permite (abierto)."""
    if not configured():
        return None
    token = (authorization or "").removeprefix("Bearer ").strip()
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado")
    return user


class LoginIn(BaseModel):
    username: str
    password: str


@router.get("/status")
def status(authorization: str | None = Header(None)):
    cfg = configured()
    authed = (not cfg) or bool(verify_token((authorization or "").removeprefix("Bearer ").strip()))
    return {"configured": cfg, "authenticated": authed}


@router.post("/login")
def login(body: LoginIn):
    user, ph = get_setting("auth_user"), get_setting("auth_pass_hash")
    if not (user and ph) or body.username != user or not verify_password(body.password, ph):
        raise HTTPException(status_code=401, detail="Usuario o contraseña inválidos")
    return {"token": make_token(user), "user": user}
