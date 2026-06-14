# nz-monitor — observabilidad para Netezza

Web para vigilar Netezza: tablas mal distribuidas (skew), espacio por base de datos,
salud de conexiones y archivos viejos en SFTP. Diseñada para **no saturar** Netezza
(ver `AGENTS.md` y `ARCHITECTURE.md`).

## Conector a Netezza
Usa **nzpy** (conector 100% Python). **No** requiere Java ni driver ODBC — basta `pip install`.
(El `backend/drivers/nzjdbc.jar` queda solo como fallback JDBC opcional.)

## Qué necesita el otro usuario para correrlo

### Camino A — Docker (recomendado)
1. **El código** (este repo).
2. **Docker Desktop**.
3. Copiar `.env.example` → `.env` y completarlo.
4. Tener **red y credenciales** hacia el servidor Netezza.
```bash
docker compose up --build
# escala (con redis):  docker compose --profile scale up --build
```
Abrir: http://localhost:8080

### Camino B — sin Docker
1. **Python 3.12** y **Node 20+**.
2. Backend:
   ```bash
   cd backend
   python -m venv .venv && .venv\Scripts\activate   # Linux/Mac: source .venv/bin/activate
   pip install -r requirements.txt
   copy ..\.env.example .env                          # editar
   uvicorn main:app --reload --port 8000
   ```
3. Recolector (proceso aparte):
   ```bash
   python -m collector
   ```
4. Frontend:
   ```bash
   cd frontend && npm install && npm run dev
   ```

> Con nzpy **no** hay que instalar driver ODBC ni Java: esa parte (el "gotcha" clásico) desaparece.

## Documentación
- `AGENTS.md` — reglas de desarrollo (regla de oro: pasivo vs en vivo).
- `ARCHITECTURE.md` — diseño (recolector → SQLite → API + ruta en vivo).
- `ROADMAP.md` — migración por fases.
- `DEVELOPMENT.md` — setup, comandos, convenciones.

## Estructura
```
nz-monitor-v2/
├─ AGENTS.md ARCHITECTURE.md ROADMAP.md DEVELOPMENT.md README.md
├─ docker-compose.yml  pyproject.toml  .pre-commit-config.yaml  .env.example
└─ backend/
   ├─ requirements.txt  Dockerfile
   ├─ netezza/connection.py     # nzpy + pool
   ├─ collector/                # recolector (APScheduler) [pendiente]
   ├─ cache/                    # CacheBackend / EventBus [pendiente]
   └─ drivers/nzjdbc.jar        # fallback JDBC opcional
```
