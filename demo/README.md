# demo/ — prototipo funcional (referencia visual)

Prototipo en un solo archivo (`app.py`, FastAPI + nzpy) que valida look & feel, flujo y queries
contra Netezza real. **Es desechable**: el producto se construye en React+TS (ver `../AGENTS.md`).
Sirve como referencia de UI y de las queries (ver `../NETEZZA.md`).

## Qué demuestra
- Resumen por base, tablas con skew/distribución, **uso por dataslice** (mapa), **carga por dataslice**.
- Ordenar por clic en encabezado, paginación, selector de base (+ "Todas las bases").
- Detalle de tabla: **última acción** + actividad + dataslices que ocupa.
- Tema claro/oscuro, responsive, PWA. Patrón pasivo (auto) + en vivo (on-demand).

## Cómo correrlo
Requiere `pip install fastapi "uvicorn[standard]" nzpy`. Pasa las credenciales por entorno
(**no hay secretos en el código**):

```bash
set NZ_HOST=tu-host         # Linux/mac: export NZ_HOST=...
set NZ_PORT=5480
set NZ_DB=TU_BASE
set NZ_USER=usuario
set NZ_PASS=clave
uvicorn app:app --host 0.0.0.0 --port 8099
```
Abrir http://localhost:8099 (o la IP de la PC en la red).

> Nota: sin login y muestra datos reales — usar solo en red de confianza.
