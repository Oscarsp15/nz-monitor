# AGENTS.md — nz-monitor (observabilidad para Netezza)

> Reglas para cualquier agente de IA o desarrollador que trabaje en este proyecto.
> **Léelo antes de tocar código.** Si una decisión contradice este archivo, gana este archivo
> (o se actualiza este archivo primero, justificando el cambio).

---

## 0. Propósito del proyecto

Web de **observabilidad para Netezza**. Sirve para:
- Detectar **tablas mal distribuidas** (skew de distribución).
- Ver **espacio en disco por base de datos**.
- Vigilar **salud de conexiones** (Netezza y SFTP).
- Encontrar **archivos viejos / espacio en SFTP**.

Usuarios objetivo: **DBAs / ingenieros de datos** que muchas veces están **depurando tablas para
recuperar espacio y necesitan ver el resultado real de lo que acaban de hacer**.

---

## 1. Lo que hay que entender de Netezza (no negociable)

Netezza es un **data warehouse MPP**, NO una base transaccional:
- El **costo de abrir una sesión y de cada query es alto** (está hecho para pocas consultas grandes,
  no para muchas consultas pequeñas y frecuentes).
- Por eso, **el polling automático multiplicado por pestañas/usuarios la satura.** Ese es el
  problema arquitectónico #1 a evitar.

---

## 2. 🟡 REGLA DE ORO: frescura *bajo demanda*, no *en bucle*

Hay **dos clases de consulta** con necesidades opuestas. Tratarlas igual es el error de raíz.

| Clase | Ejemplos | Quién la dispara | ¿Fresca al segundo? | Estrategia |
|---|---|---|---|---|
| **Vigilancia pasiva** | dashboard, alerts, salud, overview de espacio | un **timer**, en cada pestaña, mire o no alguien | No | **Recolector + caché** (ver §4) |
| **Investigación bajo demanda** | skew de UNA tabla, espacio de UNA BD que acabo de depurar | **el usuario, al hacer clic** | **Sí, en vivo y real** | **Query directa a Netezza, sin caché** |

Principios derivados:
1. **Lo que el usuario está depurando se consulta EN VIVO** al pedirlo. Nunca mostrar dato cacheado
   en una vista de investigación activa.
2. **Botón "Actualizar ahora"** (force-refresh que salta cualquier caché) en toda vista de análisis.
3. **"Modo en vivo" acotado**: toggle por-vista (off por defecto) que refresca *solo esa vista*
   cada 15–30 s mientras el usuario la mira (p. ej. ver bajar el espacio durante un purge).
   Una sesión + una query cada 20 s por unos minutos → Netezza ni se inmuta.
4. El que satura **no** es traer el dato real cuando se pide; es el **auto-refresh global, repetido,
   multiplicado**. Mata eso, no la frescura.

---

## 3. Stack oficial

**Backend**
- Python 3.12 · **FastAPI** · Pydantic v2
- **nzpy** para Netezza (conector 100% Python, sin Java ni driver ODBC) con **pool reutilizado**
  - Alternativa/fallback: JDBC (`backend/drivers/nzjdbc.jar` + jaydebeapi, requiere Java). No usar salvo necesidad.
- **SQLAlchemy** solo para la BD local (no para Netezza)
- **APScheduler** para el recolector en segundo plano (Airflow solo si ya hay pipelines pesados)
- **SSE** (Server-Sent Events) para empujar el overview al frontend (WebSocket solo si se necesita
  bidireccional real)
- Caché: **cachetools** (TTL en memoria) + **SQLite** como store de snapshots
- **Redis: OPCIONAL.** No al inicio (1 proceso). Se añade solo al escalar a varios
  workers/instancias (caché compartido + pub/sub + lock distribuido). Programar contra una
  interfaz `CacheBackend`/`EventBus` para que migrar a Redis sea un *swap*, no una reescritura.

**Frontend**
- **React + TypeScript (strict)** · **Vite**
- **TanStack Query** (React Query) para fetching/caché de cliente
- **Tailwind CSS**

**Datos / infra**
- **SQLite** local: auth, credenciales cifradas, snapshots de métricas
- **Docker Compose** + **Nginx** (reverse proxy)

> Mantener la estructura modular por dominio que ya existe: `auth/`, `netezza/`, `monitoring/`, `sftp/`.

---

## 4. Arquitectura objetivo

```
   RECOLECTOR (APScheduler, cada 1–5 min según el dato)
        │  (golpea Netezza/SFTP UNA vez, sin importar cuántos miran)
        ▼
     SQLite (snapshots: salud, alerts, overview de espacio)
        │
   FastAPI
     ├─ PASIVO  → lee de SQLite (instantáneo) ── push por SSE ──► navegadores
     └─ EN VIVO → query directa a Netezza SOLO cuando el usuario hace clic / "Actualizar"
```

- **Pasivo** (dashboard/alerts/overview): servir del snapshot en SQLite; empujar cambios por SSE.
  El frontend **no** hace polling para esto.
- **En vivo** (análisis de tabla/BD): endpoint que ejecuta la query real contra Netezza, on-demand.
- ⚠️ **El recolector corre como UN proceso único** (contenedor/servicio aparte, o un solo worker).
  Nunca arrancar APScheduler dentro de cada worker de la API → serían N recolectores = N golpes.

---

## 5. Reglas Netezza (críticas)

- ✅ **Reutilizar conexiones** del pool. ❌ Nunca abrir+cerrar una conexión por request.
- ❌ No reconectar sin pool por cada catálogo. (Bug actual en `_execute_with_catalog`: abre conexión
  nueva por BD → arreglar para que use pool por catálogo.)
- ❌ Quitar el `SELECT 1` de liveness en **cada** préstamo del pool (testear solo si lleva > N s inactiva).
- 🕒 **Timeout obligatorio** en toda query + posibilidad de cancelar.
- 📚 Cachear agresivo lo que casi no cambia: **esquema, lineage, definiciones** (cambian en deploys, no al minuto).
- 🐘 Queries pesadas (espacio por BD, skew global de todo el appliance) → **solo en el recolector**
  cada 5–15 min, jamás dentro de un request de dashboard.
- 🔒 Respetar bases **read-only** (ya existe `DatabaseReadOnlyError`). Netezza es **solo lectura** salvo
  acciones explícitas y autorizadas.

---

## 6. Política de frescura por dato

| Dato | Modo | Frecuencia |
|---|---|---|
| Salud de conexión | recolector (pasivo) | cada 1–2 min |
| Alerts (disco SFTP, conexión) | recolector (pasivo) | cada 2–5 min |
| Overview de espacio por BD | recolector (pasivo) | cada 5 min |
| **Espacio de UNA BD (depurando)** | **en vivo + "Actualizar" / modo live** | on-demand |
| **Skew/distribución de UNA tabla** | **en vivo**, caché 10 min, refresh manual | on-demand |
| Esquema / lineage / explorer | caché fuerte en SQLite | invalidar en deploy o manual |

---

## 7. ❌ Anti-patrones (NO hacer)

- `refetchInterval` en cada widget/página (¡y en el `Layout`, que corre en TODAS las pantallas!).
- Consultar Netezza en cada request de dashboard/alerts.
- Polling que sigue corriendo con la pestaña en segundo plano.
- Abrir una conexión nueva por cada query o por cada catálogo.
- **Cachear lo que el usuario está depurando activamente** (mostrar dato viejo en investigación).
- Concatenar strings para armar SQL dinámico (explorer/búsqueda) → usar parámetros / lista blanca.

---

## 8. Reglas de frontend

- **TanStack Query**: `staleTime` alto en lo pasivo; **pausar auto-refresh con pestaña oculta**
  (`document.visibilitychange`).
- Auto-refresh de overview: **un solo poller compartido** (contexto/SSE), **no** uno por página.
- **Botón "Actualizar ahora"** en cada vista de análisis → fuerza query real (param `?fresh=true`
  que salta caché del backend).
- **Toggle "modo en vivo"** por vista, **off por defecto**.
- Mostrar siempre el **sello de frescura**: *"actualizado hace 3 min"*.
- 🟡 **Carga atómica (regla, no escalonada).** Una vista con **varias consultas** debe **esperar a que
  todas terminen y pintar junto**, con esqueleto/atenuado mientras carga. **Prohibido** revelar
  secciones a distinto ritmo (KPIs primero, tabla después…) → da sensación de desorden. Combinar los
  estados de carga (`loading = a.isLoading || b.isLoading`) y revelar todo con un fade. Ver §12.

---

## 9. Seguridad

- Credenciales **cifradas en reposo** (`encrypt_value`/`decrypt_value`). **Nunca** loguear secretos.
- **Auth en todos los endpoints** (`Depends(get_current_user)`).
- Validación de entrada con **Pydantic**; SQL **parametrizado** o lista blanca de identificadores.
- Netezza en **modo lectura** por defecto.

---

## 10. Calidad y convenciones

- Tipado estricto: Pydantic v2 (back) + TS `strict` (front).
- Lint/format: **ruff + black** (Python), **eslint + prettier** (TS).
- Tests: **pytest** (back), **vitest** (front). Probar el recolector y la ruta "en vivo" por separado.
- Estructura por dominio; funciones pequeñas; sin lógica de Netezza en los routers (va en servicios).
- Documentar en `docs/ARCHITECTURE.md` cualquier cambio de arquitectura.

---

## 11. Checklist antes de mergear (para el agente)

- [ ] ¿La nueva vista es **pasiva** o **bajo demanda**? ¿Aplicó la estrategia correcta (§2/§6)?
- [ ] ¿Algún `refetchInterval` nuevo? ¿Está justificado y pausado en background?
- [ ] ¿Reutiliza el pool de Netezza? ¿Sin reconexión por catálogo?
- [ ] ¿Las queries tienen timeout?
- [ ] ¿Datos de investigación se sirven **en vivo**, no cacheados?
- [ ] ¿Endpoints con auth y entrada validada?
- [ ] ¿Las vistas con varias consultas cargan **atómicas** (todo junto, atenuado mientras), sin aparición escalonada? (§8/§12)

---

## 12. UX — lecciones del prototipo (obligatorias)

Validadas construyendo el demo con datos reales. Aplicarlas en el producto.

- **Carga atómica en cambios de contexto.** Al cambiar base / orden / dataslice, traer todo lo
  dependiente con un solo `Promise.all` y **pintar junto**. Nunca actualizaciones escalonadas
  (espacio primero, tabla después) → se ven desordenadas. Atenuar mientras carga.
- **Feedback instantáneo.** Las selecciones (p. ej. elegir un dataslice) deben reflejarse en la UI
  **al instante**, antes de que vuelva la consulta. Nada de "primero busca y luego resalta".
- **Lenguaje llano (sin jerga interna).** En la UI: nada de *snapshot, caché, recolector, pasivo/en vivo*.
  Sí se usan términos del **dominio** que el DBA conoce (skew, distribución, dataslice). Ver [[design]].
- **Tema claro + oscuro**, recordando la elección y respetando el del sistema.
- **Móvil / PWA**: respetar el área segura (notch/status bar), pintar el `html` con el color del tema
  (overscroll), e instalable (manifest + iconos). Probar en celular real.
- **Tablas densas**: ordenar por **clic en el encabezado** (lo intuitivo), **paginación**, columnas
  Base/Owner. Ahí es donde brilla el framework (TanStack Table) — no reinventarlo a mano.
- **Investigación on-demand**: el detalle de una tabla (última acción, dataslices que ocupa) va en una
  **vista aparte con "← Volver"**, y consulta puntual al abrir (no en bloque para todas las filas).

## 13. Datos / queries de Netezza

Las vistas del sistema, las **queries probadas** (resumen, tablas+skew+distribución, uso por dataslice,
carga por tabla por dataslice, última acción) y los **gotchas** están en **[NETEZZA.md](NETEZZA.md)**.
Reusar de ahí; no reinventar SQL. El reporte batch completo está en el DAG
`reporte_distribucion_tablas.py` (Airflow/WSL).
