# DEVELOPMENT.md — setup y convenciones

## Requisitos
- Python 3.12, Node 20+, Docker + Docker Compose
- Driver ODBC de Netezza instalado (para conexiones reales)

## Arranque rápido (dev)
```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env       # editar credenciales/secret
uvicorn main:app --reload --port 8000

# Recolector (proceso aparte)
python -m collector

# Frontend
cd frontend
npm install
npm run dev
```

## Con Docker
```bash
docker compose up --build                 # backend + collector + frontend + nginx
docker compose --profile scale up --build # + redis (solo si escalas)
```

## Calidad de código (obligatorio antes de commitear)
```bash
# Python
ruff check . --fix      # lint
black .                 # formato
mypy backend            # tipos
pytest                  # tests

# Frontend
npm run lint            # eslint
npm run format          # prettier
npm run typecheck       # tsc --noEmit
npm run test            # vitest
```
Instala los hooks para que corra solo: `pre-commit install`.

## Convenciones
- **Backend:** estructura por dominio (`auth/`, `netezza/`, `monitoring/`, `sftp/`, `collector/`).
  Routers finos; la lógica vive en servicios. Pydantic v2 en toda entrada/salida.
- **Frontend:** TS `strict`. Un hook por recurso. Nada de `any`. Tailwind para estilos.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`...).
- **Ramas:** trabajar en rama, PR con checklist de `AGENTS.md §11`.

## Reglas que el linter NO atrapa (revisar a mano)
- ¿Vista pasiva o en vivo? ¿Estrategia correcta? (ver `AGENTS.md §2`)
- ¿Algún polling nuevo? ¿Pausado en background? ¿Un solo poller?
- ¿Query a Netezza con timeout y desde el pool?
- ¿Datos de investigación servidos en vivo (no cacheados)?

## Tests mínimos por feature
- Endpoint pasivo: que lea snapshot y **no** llame a Netezza (mock que falle si lo llaman).
- Endpoint en vivo: que `?fresh=true` salte el caché.
- Recolector: que haga upsert del snapshot y publique evento.
