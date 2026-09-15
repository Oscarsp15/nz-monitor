## Qué cambia y por qué

<!-- El problema real que resuelve, no el listado de archivos tocados. -->

## Cómo se comprobó

<!-- Números medidos, no impresiones. Si tocaste consultas a Netezza: tiempo antes y después. -->

- [ ] `pytest -q` en verde
- [ ] `ruff check` limpio en los archivos tocados
- [ ] `npm run typecheck && npm run lint && npm run build` (si tocaste frontend)

## Checklist de AGENTS.md §11

- [ ] ¿La vista nueva es **pasiva** o **bajo demanda**? ¿Aplicó la estrategia correcta (§2/§6)?
- [ ] ¿Algún `refetchInterval` nuevo? ¿Justificado y pausado en segundo plano?
- [ ] ¿Reutiliza el pool de Netezza, sin reconexión por catálogo?
- [ ] ¿Las consultas tienen timeout?
- [ ] ¿Los datos de investigación se sirven en vivo (o con revalidación visible, §2.1)?
- [ ] ¿Endpoints con auth y entrada validada?
- [ ] ¿Las vistas con varias consultas cargan **atómicas**?
- [ ] ¿Se actualizó la documentación que este cambio deja desfasada?
