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

## Primer acceso (usuarios y roles)

La app **siempre pide login**. En el primer arranque, si la base local no tiene ningún usuario,
se crea el administrador inicial con lo que haya en `.env`:

```bash
ADMIN_USER=admin
ADMIN_PASSWORD=admin      # cámbialo antes de exponer la app
```

Ese usuario se crea con **cambio de contraseña forzado**: al entrar por primera vez la web obliga
a poner una nueva (mínimo 8 caracteres) antes de dejar usar nada más. Después, desde
**Usuarios** (solo admin) se dan de alta los demás.

Si venías de la versión con **un solo usuario** (guardado en `app_setting`), al arrancar se migra
solo: ese usuario pasa a ser `admin` con su misma contraseña y las claves viejas se borran.

### Roles

| Rol | Puede |
|---|---|
| `viewer` | ver todo lo ya recolectado (dashboard, tablas, dataslices, alertas, SFTP) |
| `operador` | lo anterior + **"Actualizar ahora" / modo en vivo** (`fresh=true`) y probar conexiones |
| `admin` | todo + **Ajustes** y **Usuarios** |

Un `viewer` que intente forzar una consulta en vivo recibe un 403 con el motivo.
Si pierdes el acceso de admin, borra la fila del usuario en `app_user` (SQLite) o vacía la tabla
y reinicia: se vuelve a sembrar el admin de `.env`.

## Documentación
- `AGENTS.md` — reglas de desarrollo (regla de oro: pasivo vs en vivo).
- `ARCHITECTURE.md` — diseño (recolector → SQLite → API + ruta en vivo).
- `ROADMAP.md` — migración por fases.
- `DEVELOPMENT.md` — setup, comandos, convenciones.

## Estructura
```
nz-monitor-v2/
├─ AGENTS.md ARCHITECTURE.md ROADMAP.md DEVELOPMENT.md NETEZZA.md DESIGN.md README.md
├─ docker-compose.yml  pyproject.toml  .pre-commit-config.yaml  .env.example
├─ backend/
│  ├─ requirements.txt  Dockerfile  main.py  config.py
│  ├─ netezza/          # nzpy + pool, queries probadas, ruta "en vivo" (?fresh=true)
│  ├─ collector/        # recolector (APScheduler, proceso único): jobs + __main__
│  ├─ cache/            # CacheBackend / EventBus (memoria hoy, Redis al escalar)
│  ├─ auth/             # sesión JWT, roles y dependencias de permisos
│  ├─ users/            # administración de usuarios (solo admin)
│  ├─ store/            # SQLite: snapshots, ajustes cifrados y usuarios (app_user)
│  ├─ monitoring/       # endpoints PASIVOS (leen snapshots, no tocan Netezza)
│  └─ drivers/nzjdbc.jar # fallback JDBC opcional
└─ tests/               # pytest (cache, snapshots, recolector, pasivo, fresh)
```

## Endpoints (Fase 2/3)
- **Sesión**: `GET /api/auth/status`, `POST /api/auth/login`, `GET /api/auth/me`,
  `POST /api/auth/change-password`. **Usuarios (admin)**: `GET|POST /api/users`,
  `PATCH|DELETE /api/users/{id}`.
- **Pasivos** (leen snapshots, sin tocar Netezza): `GET /api/monitoring/health`, `GET /api/monitoring/space`.
- **En vivo / análisis** (caché con bypass): `GET /api/overview|tables|owners|dataslices?fresh=true`
  ("Actualizar ahora"), `GET /api/table`, `GET /api/table/slices`.
- El recolector (`python -m collector`) refresca salud y espacio cada N segundos (ver `.env`).
