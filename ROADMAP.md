# ROADMAP.md — migración por fases

No reescribir todo de golpe. Migrar el `nz-monitor` actual por fases, midiendo el alivio de carga
en Netezza en cada paso. Cada fase es desplegable por sí sola.

> **Estado (v2.16):** Fase 1 ✅ · Fase 2 ✅ · Fase 3 ✅ (`?fresh=true` + modo en vivo) ·
> Frontend React/PWA ✅ (nav por niveles: bottom nav móvil + sidebar desktop) · Vistas: Resumen
> (dashboard con tendencias + disco SFTP), Tablas/Owners/Dataslices con drill-down ds→tablas→detalle,
> Alertas, Ajustes · Alertas (dataslice + disco SFTP) por snapshot · **SFTP** (disco + archivos
> viejos) · Config 100% por la web (cifrada) · **Fase 4 SSE ✅** (dashboard en vivo) · **Auth ✅**
> (**multiusuario con roles admin/operador/viewer, login obligatorio**; ver ARCHITECTURE §7) ·
> **Búsqueda de código en SPs ✅**.
> **Eliminado:** integración de IA (Groq) y notificaciones/asistente por Telegram — quitadas del
> backend (decisión de producto), ya no forman parte del alcance.

**Pendiente:** lineage / grafo de dependencias de SPs · Fase 5 Redis (solo al escalar) ·
auditoría de acciones por usuario (quién forzó qué consulta en vivo).

**Rendimiento del catálogo (medido en el appliance, on-prem, VPN):**
- Resumen de base en **una** consulta (`SUM(CASE WHEN skew>8 …)` en el mismo escaneo):
  **2.13 s → 1.05 s** (DESA_RIESGOS, 11 155 tablas).
- `db=*` sin N+1 (distribución de toda la página en un `UNION ALL`): **3.17 s → 2.80 s** y,
  sobre todo, **8 consultas → 2**, constante con el nº de bases de la página.
- Timeout de **conexión** (`NETEZZA_CONNECT_TIMEOUT`, 10 s): con la VPN caída el request ya no
  se cuelga sin límite.
- Los pasivos degradan `ok → stale` a 3× el intervalo del recolector (ya no se sirve un dato de
  11 h como actual).

## Fase 0 — Medir (antes de tocar nada)
- Instrumentar: contar queries/seg a Netezza y latencia por endpoint.
- Identificar las vistas que más golpean (esperado: dashboard/alerts/health por el polling).
- **Meta:** tener un número "antes" para comparar.

## Fase 1 — Quick wins (días, bajo riesgo) ⚡
1. **Caché TTL del lado servidor** en `/health/all` y `/alerts` (~60s). Pestañas/usuarios comparten resultado.
2. **Frontend:** quitar polling redundante del `Layout`; pausar auto-refresh con pestaña oculta;
   subir intervalos (health 1–2 min, espacio 5 min).
3. **Pool:** quitar el `SELECT 1` de cada préstamo; arreglar `_execute_with_catalog` para usar pool.
- **Resultado esperado:** caída fuerte de queries sin cambiar arquitectura.

## Fase 2 — Recolector + snapshots (la solución de fondo) 🏗️
1. Servicio `collector` (proceso único, APScheduler) que recolecta salud/alerts/overview a SQLite.
2. Reapuntar los endpoints **pasivos** a leer del snapshot (ya no tocan Netezza).
3. Sello de frescura ("actualizado hace X") en el front.
- **Resultado:** la carga pasiva en Netezza pasa a ser constante (1 recolector), independiente de usuarios.

## Fase 3 — En vivo bien hecho (investigación) 🔎
1. Endpoints "en vivo" para análisis de tabla/BD con `?fresh=true` y timeout.
2. Botón **"Actualizar ahora"** + toggle **"modo en vivo"** acotado por vista.
- **Resultado:** datos reales al depurar, sin reintroducir polling global.

## Fase 4 — Push por SSE 📡
1. `EventBus` en proceso + endpoint `/stream` (SSE).
2. El recolector publica; el front deja de hacer polling de lo pasivo y reacciona a eventos.
- **Resultado:** cero polling de fondo; el front se entera al instante cuando hay snapshot nuevo.

## Fase 5 — Escala (solo si hace falta) 📈
- Si se va a multi-worker/multi-instancia: introducir **Redis** (`RedisCache` + `RedisEventBus`)
  detrás de las interfaces ya existentes, y lock distribuido para el recolector.
- CI/CD, métricas (Prometheus/Grafana), alertas reales.

---

### Orden recomendado de arranque
**Fase 1 ya** (alivio inmediato) → **Fase 2** (arregla la raíz) → 3 → 4. Redis (Fase 5) solo si escalas.
