"""Interfaces enchufables de caché y bus de eventos (ver ARCHITECTURE.md §2.3).

Programar contra estos Protocols permite migrar a Redis al escalar (Fase 5 del ROADMAP)
como un *swap* de implementación, sin tocar el resto del código.
"""
from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CacheBackend(Protocol):
    """Caché clave→valor con TTL por entrada."""

    def get(self, key: str) -> Any | None: ...

    def set(self, key: str, value: Any, ttl: int) -> None: ...

    def delete(self, key: str) -> None: ...


@runtime_checkable
class EventBus(Protocol):
    """Bus publish/subscribe para empujar cambios al frontend (SSE, Fase 4)."""

    def publish(self, channel: str, payload: dict) -> None: ...

    def subscribe(self, channel: str) -> AsyncIterator[dict]: ...
