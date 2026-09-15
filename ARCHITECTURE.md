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

**`stale` lo decide la API al servir, no el recolector.** El `status` guardado solo sabe cómo fue
*esa* recolección; con el recolector parado, un snapshot de 11 h se seguía sirviendo como `ok`.
`monitoring/router._serve` compara `age_seconds` con el intervalo del recolector de **esa** métrica
(`collector_*_interval_seconds`, ver `AGENTS.md §6`) por `STALE_FACTOR` (3×, margen para un ciclo
perdido) y degrada `ok → stale`. Un `error` real nunca se tapa con `stale`. La respuesta lleva
`stale_after_seconds` para que el frontend pueda explicar el umbral.

## 4. Flujo "en vivo" (investigación)
1. Usuario abre análisis de una tabla / da "Actualizar".
2. Front llama al endpoint en vivo (con `?fresh=true` si forzó).
3. API toma conexión **del pool**, ejecuta la query con **timeout**, devuelve resultado real.
4. (Opcional) cachea 5–10 min para clics repetidos, pero `fresh=true` siempre lo salta.
5. **Toda respuesta de investigación lleva `at` (marca de tiempo del dato) y `from_cache`**: es el
   contrato con el que el frontend pinta el sello y el estado "actualizando…" de la revalidación
   visible (`AGENTS.md §2.1`). Incluye `/api/table` y `/api/table/slices`, que son siempre en vivo
   (`from_cache: false`).

## 5. Pool de conexiones Netezza
- Pool por `host:port:db:user`, reutilizado. Sin abrir/cerrar por request.
- **Timeout de conexión** (`NETEZZA_CONNECT_TIMEOUT`, 10 s): sin él, con la VPN caída el `connect()`
  esperaba el timeout de TCP del sistema (minutos) y el request quedaba colgado. `nzpy` deja ese
  timeout pegado al socket toda la sesión, así que tras conectar se sube a
  `NETEZZA_QUERY_TIMEOUT + 5 s` (si no, una consulta de catálogo legítima de 5 s moriría en un
  socket de 10 s). El límite real de la query lo sigue poniendo Netezza (`SET QUERY_TIMEOUT`).
- Test de liveness **perezoso** (solo si la conexión lleva > N s ociosa), no en cada préstamo.
- `_execute_with_catalog`: usar pool por catálogo (no reconectar a pelo).
- Timeout y cancelación en toda query.

## 6. Realtime (SSE)
- SSE (un sentido server→cliente) cubre el 100% del caso pasivo. Más simple que WebSocket.
- El front se suscribe a `/stream`; al recibir un evento, invalida/actualiza la query de TanStack.
- WebSocket solo si en el futuro hay interacción bidireccional real.

## 7. Autenticación y roles

Multiusuario con JWT. **El login es obligatorio siempre**: no hay "modo abierto".

```
POST /api/auth/login ──► verifica pbkdf2 contra app_user ──► JWT {sub, uid, role, exp}
       │
       ▼
cada request:  Authorization: Bearer <jwt>
       │   require_auth: decodifica el token Y relee app_user (rol, activo)
       ▼
require_role(min)          deny_live_for_viewer
 (viewer<operador<admin)    (viewer + ?fresh/live=true → 403)
```

- **Módulos**: `auth/security.py` (pbkdf2 + JWT), `auth/deps.py` (dependencias `require_auth`,
  `require_role`, `deny_live_for_viewer`, `require_auth_stream`), `auth/service.py` (login y
  cambio de contraseña), `auth/bootstrap.py` (migración + siembra), `auth/router.py` (sesión).
  `users/` es un dominio aparte: administración de cuentas (solo admin), distinto permiso y
  distinto ciclo de vida que la sesión.
- **El rol se relee de la BD en cada request**, no se confía en el del token: desactivar o borrar
  un usuario invalida sus tokens al instante (401).
- **Permisos por router** (`main.py`), nunca con `if` repetidos en cada endpoint:
  `/api/users` y `/api/settings` → admin (excepción: `POST /api/settings/sftp/test`, que abre una
  conexión real, es de operador); `/api/monitoring` → cualquier autenticado;
  `netezza`/`sftp` → autenticado, y `viewer` no puede mandar `fresh=true`/`live=true` (403).
- ⚠️ **Dos límites de `deny_live_for_viewer`, ambos ya cerrados y con test**:
  1. *Qué mira*: solo el query string. Las rutas que consultan Netezza **siempre** (`/api/table`,
     `/api/table/slices`: 4 consultas, una es el `LIKE` sobre `NZ_QUERY_HISTORY`) no tienen `fresh`
     que mirar, así que declaran `require_role("operador")` en la propia ruta.
  2. *Cómo lo lee*: con `TypeAdapter(bool)`, el mismo parser que FastAPI aplica a `fresh: bool`.
     Una lista literal de valores "verdaderos" se desincroniza del framework (pydantic acepta
     también `t`/`y`, y por ahí se colaba la consulta en vivo con rol `viewer`).
- **SSE**: `EventSource` no manda cabeceras, así que `/api/stream` (y solo ese) acepta
  `?token=<jwt>` además de la cabecera `Authorization`.
- **Esquema** (mismo SQLite que snapshots/ajustes; se crea solo):

```sql
CREATE TABLE IF NOT EXISTS app_user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE COLLATE NOCASE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('admin','operador','viewer')),
  active INTEGER NOT NULL DEFAULT 1,
  must_change_password INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  last_login_at TEXT
);
```

- **Arranque** (`bootstrap_users()`, en el `lifespan` de la API y en `python -m collector`):
  1. si existen las claves KV `auth_user`/`auth_pass_hash` (login viejo de 1 usuario), se crea ese
     usuario como `admin` **reusando el hash** y se borran las claves;
  2. si no hay ningún usuario, se siembra `ADMIN_USER`/`ADMIN_PASSWORD` con
     `must_change_password=1`.
  Es idempotente y nunca escribe contraseñas en el log.
