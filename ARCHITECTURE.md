# ARCHITECTURE.md — nz-monitor

Diseño técnico. Complementa `AGENTS.md` (las reglas mandan; esto explica el *cómo*).

## 1. Vista general

```
                 ┌──────────────────────────────────────────────┐
                 │  RECOLECTOR (proceso único, APScheduler)       │
                 │  cada 1–5 min: golpea Netezza/SFTP UNA vez     │
                 └───────────────┬──────────────────────────────┘
                                 │ escribe snapshot
                                 ▼
                          ┌────────────┐
                          │  SQLite     │  snapshots, auth, credenciales cifradas
                          └─────┬───────┘
                                │ lee
        ┌───────────────────────┴───────────────────────┐
        │                  FastAPI                        │
        │  PASIVO  → snapshot (SQLite) ── push SSE ──┐    │
        │  EN VIVO → query directa a Netezza (clic)  │    │
        └────────────────────────────────────────────┼────┘
                                                       ▼
                                              React + TanStack Query
                                   (SSE para pasivo · fetch on-click para vivo)
```

## 2. Componentes

### 2.1 Recolector (`collector/`)
- Proceso **único** (contenedor `collector` o `python -m collector`). NUNCA dentro de cada worker API.
- APScheduler con jobs por dato (ver frecuencias en `AGENTS.md §6`).
- Cada job: 1) ejecuta la query/comando, 2) hace `upsert` del snapshot en SQLite,
  3) publica un evento en el `EventBus` (para que la API empuje por SSE).
- Tolerante a fallos: si Netezza no responde, marca el snapshot como `stale` con error, no rompe.

### 2.2 API (`backend/`)
- **Pasivo**: endpoints que **solo leen SQLite** (`/health/all`, `/alerts`, `/space/overview`). Nunca tocan Netezza.
- **En vivo**: endpoints de análisis (`/analysis/table/{...}`, `/space/db/{db}`) que ejecutan la
  query real on-demand. Aceptan `?fresh=true` para saltar cualquier caché.
- **SSE**: `GET /stream` emite los eventos del `EventBus` a los navegadores suscritos.

### 2.3 Interfaces enchufables (clave para Redis-opcional)
```python
class CacheBackend(Protocol):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any, ttl: int) -> None: ...

class EventBus(Protocol):
    def publish(self, channel: str, payload: dict) -> None: ...
    def subscribe(self, channel: str) -> AsyncIterator[dict]: ...
```
- **Hoy (1 proceso):** `InMemoryCache` (cachetools) + `InProcessEventBus` (asyncio.Queue).
- **Al escalar:** `RedisCache` + `RedisEventBus`. Se cambia la implementación en el contenedor de DI,
  el resto del código no se entera.

## 3. Esquema de snapshots (SQLite)

```sql
CREATE TABLE metric_snapshot (
  id            INTEGER PRIMARY KEY,
  metric_type   TEXT NOT NULL,         -- 'health' | 'alerts' | 'space_overview'
  credential_id INTEGER,
  payload_json  TEXT NOT NULL,         -- el resultado serializado
  collected_at  TIMESTAMP NOT NULL,    -- cuándo se recolectó (para el sello "hace X")
  status        TEXT NOT NULL,         -- 'ok' | 'stale' | 'error'
  error         TEXT
);
CREATE INDEX ix_snapshot_lookup ON metric_snapshot(metric_type, credential_id, collected_at DESC);
```
La API sirve el `payload_json` más reciente y devuelve también `collected_at` para el sello de frescura.

## 4. Flujo "en vivo" (investigación)
1. Usuario abre análisis de una tabla / da "Actualizar".
2. Front llama al endpoint en vivo (con `?fresh=true` si forzó).
3. API toma conexión **del pool**, ejecuta la query con **timeout**, devuelve resultado real.
4. (Opcional) cachea 5–10 min para clics repetidos, pero `fresh=true` siempre lo salta.

## 5. Pool de conexiones Netezza
- Pool por `host:port:db:user`, reutilizado. Sin abrir/cerrar por request.
- Test de liveness **perezoso** (solo si la conexión lleva > N s ociosa), no en cada préstamo.
- `_execute_with_catalog`: usar pool por catálogo (no reconectar a pelo).
- Timeout y cancelación en toda query.

## 6. Realtime (SSE)
- SSE (un sentido server→cliente) cubre el 100% del caso pasivo. Más simple que WebSocket.
- El front se suscribe a `/stream`; al recibir un evento, invalida/actualiza la query de TanStack.
- WebSocket solo si en el futuro hay interacción bidireccional real.
