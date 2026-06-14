"""Implementaciones en memoria (1 proceso) de CacheBackend y EventBus.

- `InMemoryCache`: TTL por-clave, thread-safe. Sirve para el cache-aside de los
  endpoints (ver AGENTS.md §2). Al escalar a varios workers se cambia por `RedisCache`.
- `InProcessEventBus`: pub/sub con `asyncio.Queue` por suscriptor. Cubre el caso de SSE
  *dentro de un proceso*. A través de procesos (API vs recolector) el canal real es el
  snapshot en SQLite; para pub/sub cross-proceso se usa Redis (Fase 5).
"""
import asyncio
import contextlib
import threading
import time
from collections.abc import AsyncIterator
from typing import Any


class InMemoryCache:
    """Caché TTL por-clave, segura entre hilos (usa reloj monótono)."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._lock:
            hit = self._data.get(key)
            if hit is None:
                return None
            value, expires_at = hit
            if expires_at < now:
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        with self._lock:
            self._data[key] = (value, time.monotonic() + ttl)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class InProcessEventBus:
    """Pub/sub en proceso. Cada `subscribe` recibe su propia cola asíncrona."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._lock = threading.Lock()

    def publish(self, channel: str, payload: dict) -> None:
        with self._lock:
            queues = list(self._subscribers.get(channel, ()))
        for q in queues:
            # suscriptor lento: descartar, no bloquear al publicador
            with contextlib.suppress(asyncio.QueueFull):
                q.put_nowait(payload)

    async def subscribe(self, channel: str) -> AsyncIterator[dict]:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        with self._lock:
            self._subscribers.setdefault(channel, []).append(q)
        try:
            while True:
                yield await q.get()
        finally:
            with self._lock:
                subs = self._subscribers.get(channel)
                if subs and q in subs:
                    subs.remove(q)
