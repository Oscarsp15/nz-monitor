"""Configuración (pydantic-settings, lee de entorno / .env).

Los `.env` se resuelven por RUTA ABSOLUTA, no relativa al directorio desde el que se lanza el
proceso: si no, arrancar la API desde `backend/` leía otro archivo que arrancarla desde la raíz,
y una clave puesta en el `.env` equivocado se ignoraba en silencio (ver `DEFAULT_SECRET_KEY`).
Se leen los dos y el de `backend/` gana, que es el que existe en el despliegue del servidor.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_HERE = Path(__file__).resolve().parent          # …/backend
_ROOT = _HERE.parent                             # raíz del repo

# Default de desarrollo: está en el código fuente, o sea que es PÚBLICO. Con él se puede forjar
# un JWT de cualquier usuario, así que la app se niega a arrancar si sigue puesto (ver
# `check_secret_key`).
DEFAULT_SECRET_KEY = "nz-monitor-dev-secret-change-me"  # noqa: S105


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_ROOT / ".env", _HERE / ".env"), extra="ignore")

    app_env: str = "development"
    # clave maestra para cifrar settings sensibles en la BD (credenciales SFTP, etc.).
    # En prod, ponla larga y aleatoria en .env. Es el unico secreto de bootstrap.
    secret_key: str = DEFAULT_SECRET_KEY
    # api = solo sirve la API (NO arranca el recolector) · collector = proceso único del recolector
    app_role: str = "api"
    jwt_expire_minutes: int = 480  # duración del token de login
    # Admin inicial: solo se usa si la BD no tiene NINGÚN usuario (primer arranque).
    # Se crea con must_change_password=1 → la web obliga a cambiarla al entrar.
    admin_user: str = "admin"
    admin_password: str = "admin"  # noqa: S105 (default de bootstrap; override en .env)
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Base local (snapshots, auth, credenciales cifradas). Ver ARCHITECTURE.md §3.
    database_url: str = "sqlite:///./data/nzmonitor.db"

    # Netezza (MVP: una conexión por entorno; en prod vendrá del store cifrado)
    netezza_host: str = ""
    netezza_port: int = 5480
    netezza_database: str = ""
    netezza_user: str = ""
    netezza_password: str = ""
    netezza_security_level: int = 0
    netezza_query_timeout: int = 30
    netezza_pool_max_size: int = 5

    # Recolector (proceso único, APScheduler) — frecuencias en segundos (ver AGENTS.md §6)
    collector_health_interval_seconds: int = 90
    collector_alerts_interval_seconds: int = 180
    collector_space_interval_seconds: int = 300

    # Caché / EventBus enchufables (ver ARCHITECTURE.md §2.3). memory hoy; redis al escalar.
    cache_backend: str = "memory"
    eventbus_backend: str = "memory"
    redis_url: str = "redis://localhost:6379/0"

    # SFTP (timeouts; credenciales se configuran cifradas desde la web)
    sftp_connection_timeout: int = 15
    sftp_command_timeout: int = 30

    # caché de endpoints pasivos / "en vivo" (cache-aside; lo salta ?fresh=true)
    overview_ttl: int = 30
    tables_ttl: int = 60
    dataslices_ttl: int = 60
    live_query_cache_seconds: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()


class InsecureSecretKeyError(RuntimeError):
    """SECRET_KEY sin configurar: cualquiera podría firmar un token válido."""


def check_secret_key(settings: Settings | None = None) -> None:
    """Aborta el arranque si SECRET_KEY sigue siendo el default público del repo.

    Se llama al arrancar la API y el recolector. Falla pronto y ruidoso: el modo degradado
    silencioso es justo lo que dejaba la API abierta de par en par.
    """
    s = settings or get_settings()
    if s.secret_key.strip() in ("", DEFAULT_SECRET_KEY):
        raise InsecureSecretKeyError(
            "SECRET_KEY no está configurada: con el valor por defecto (que está en el código "
            "fuente) cualquiera puede firmar un token de administrador. Ponla en el .env que "
            f"lee este proceso ({_HERE / '.env'} o {_ROOT / '.env'}). Puedes generarla con: "
            "  python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
