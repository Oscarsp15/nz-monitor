"""Factory de caché y bus de eventos (singletons por proceso).

Elige la implementación según `CACHE_BACKEND` / `EVENTBUS_BACKEND`. Hoy solo `memory`;
`redis` queda reservado para la Fase 5 del ROADMAP (multi-worker/multi-instancia).
"""
from config import get_settings

from .base import CacheBackend, EventBus
from .memory import InMemoryCache, InProcessEventBus

__all__ = ["CacheBackend", "EventBus", "get_cache", "get_event_bus"]

_cache: CacheBackend | None = None
_bus: EventBus | None = None


def get_cache() -> CacheBackend:
    global _cache
    if _cache is None:
        backend = get_settings().cache_backend.lower()
        if backend == "memory":
            _cache = InMemoryCache()
        elif backend == "redis":
            raise NotImplementedError(
                "RedisCache es Fase 5 del ROADMAP; usa CACHE_BACKEND=memory por ahora."
            )
        else:
            raise ValueError(f"CACHE_BACKEND desconocido: {backend!r}")
    return _cache


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        backend = get_settings().eventbus_backend.lower()
        if backend == "memory":
            _bus = InProcessEventBus()
        elif backend == "redis":
            raise NotImplementedError(
                "RedisEventBus es Fase 5 del ROADMAP; usa EVENTBUS_BACKEND=memory por ahora."
            )
        else:
            raise ValueError(f"EVENTBUS_BACKEND desconocido: {backend!r}")
    return _bus
