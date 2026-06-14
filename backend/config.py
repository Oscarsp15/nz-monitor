"""Configuración (pydantic-settings, lee de entorno / .env)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    # clave maestra para cifrar settings sensibles en la BD (token Telegram, etc.).
    # En prod, ponla larga y aleatoria en .env. Es el unico secreto de bootstrap.
    secret_key: str = "nz-monitor-dev-secret-change-me"  # noqa: S105 (default de dev; override en .env)
    # api = solo sirve la API (NO arranca el recolector) · collector = proceso único del recolector
    app_role: str = "api"
    jwt_expire_minutes: int = 480  # duración del token de login
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

    # Notificaciones Telegram (push de alertas). Vacío = desactivado (no rompe).
    # chat_id puede ser un usuario, un GRUPO (id negativo, p.ej. -1001234567890) o un canal.
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    groq_api_key: str = ""  # IA opcional (alertas inteligentes); se configura desde la web

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
