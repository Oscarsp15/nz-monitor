"""Configuración (pydantic-settings, lee de entorno / .env)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Netezza (MVP: una conexión por entorno; en prod vendrá del store cifrado)
    netezza_host: str = ""
    netezza_port: int = 5480
    netezza_database: str = ""
    netezza_user: str = ""
    netezza_password: str = ""
    netezza_security_level: int = 0
    netezza_query_timeout: int = 30
    netezza_pool_max_size: int = 5

    # caché de endpoints pasivos (cache-aside; ver ROADMAP Fase 1)
    overview_ttl: int = 30
    tables_ttl: int = 60
    dataslices_ttl: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
