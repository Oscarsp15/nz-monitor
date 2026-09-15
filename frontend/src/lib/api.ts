// Cliente API tipado. En dev usa el proxy de Vite (/api → :8000); en prod, Nginx.

export interface Freshness {
  at: number
  from_cache: boolean
}

export interface OverviewResp extends Freshness {
  data: { total_gb: number; table_count: number }
  database: string | null
}

export interface Dataslice {
  id: number
  pct: number
  gb_used: number
  gb_size: number
  status: string
}

export interface TableRow {
  db: string | null
  schema: string | null
  table: string | null
  owner: string | null
  objid: number
  distribute_on: string
  space_gb: number
  skew: number
}

export interface TablesResp extends Freshness {
  rows: TableRow[]
  has_next: boolean
  database: string | null
  order: string
  page: number
}

export interface TableMeta {
  db: string
  sch: string
  owner: string
  created: string
  gb: number
  skew: number
}

export interface HistoryRow {
  tend: string
  user: string
  db: string
  verb: string
  sql: string
}

export interface TableDetailResp {
  objid: number
  table: string
  meta?: TableMeta | null
  meta_error?: string
  history?: HistoryRow[]
  history_error?: string
}

export interface Snapshot<T> {
  metric: string
  status: 'ok' | 'stale' | 'error' | 'empty'
  collected_at: string | null
  age_seconds: number | null
  error?: string | null
  data: T | null
}

export interface SpaceByDb {
  databases: { db: string; table_count: number; gb: number }[]
}

export interface AlertItem {
  level: 'warn' | 'crit'
  kind: string
  ds?: number
  value: number
  message: string
}

export interface DsTableRow {
  db: string | null
  schema: string | null
  table: string | null
  owner: string | null
  objid: number
  skew: number
  gb_ds: number
  gb_total: number
}

export interface AlertsData {
  alerts: AlertItem[]
  count: number
  max_dataslice_pct: number
  sftp?: { path: string; pct: number; used: string; size: string; available: string } | null
}

export interface OwnerRow {
  owner: string
  tablas: number
  gb: number
}

// ─── Auth / usuarios ───
export type Role = 'admin' | 'operador' | 'viewer'

export interface AuthStatus {
  authenticated: boolean
  user: string | null
  role: Role | null
  must_change_password: boolean
}

export interface LoginResp {
  token: string
  user: string
  role: Role
  must_change_password: boolean
}

export interface MeResp {
  id: number
  username: string
  role: Role
  must_change_password: boolean
}

export interface AppUser {
  id: number
  username: string
  role: Role
  active: boolean
  must_change_password: boolean
  created_at: string
  last_login_at: string | null
}

const TOKEN_KEY = 'nzm-token'
export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t: string) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

function authHeaders(): Record<string, string> {
  const t = getToken()
  return t ? { Authorization: `Bearer ${t}` } : {}
}

/** Rutas donde un 401 es una respuesta esperada del formulario, no una sesión caducada. */
const NO_RELOGIN = ['/auth/login', '/auth/change-password']

function on401(status: number, path: string) {
  if (status === 401 && !NO_RELOGIN.some((p) => path.startsWith(p))) {
    clearToken()
    location.reload() // sesión caducada → vuelve a la pantalla de login
  }
}

/** 403: no romper la vista — mensaje claro y llano en vez del detalle técnico del backend. */
async function throwForStatus(res: Response, path: string): Promise<never> {
  on401(res.status, path)
  if (res.status === 403) {
    throw new Error('No tienes permisos para esta acción')
  }
  let detail = res.statusText
  try {
    detail = (await res.json()).detail ?? detail
  } catch {
    /* respuesta no-JSON */
  }
  throw new Error(`${res.status} · ${detail}`)
}

async function get<T>(path: string, params?: Record<string, string | number | boolean>): Promise<T> {
  const qs = params
    ? '?' +
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== '')
        .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
        .join('&')
    : ''
  const res = await fetch(`/api${path}${qs}`, { headers: authHeaders() })
  if (!res.ok) return throwForStatus(res, path)
  return res.json() as Promise<T>
}

async function mutate<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) return throwForStatus(res, path)
  return res.json() as Promise<T>
}

export interface SftpCfg {
  host: string
  port: number
  user: string
  has_password: boolean
  has_key: boolean
  default_path: string
  configured: boolean
}

export const api = {
  authStatus: () => get<AuthStatus>('/auth/status'),
  login: (username: string, password: string) =>
    mutate<LoginResp>('POST', '/auth/login', { username, password }),
  me: () => get<MeResp>('/auth/me'),
  changePassword: (current_password: string, new_password: string) =>
    mutate<{ ok: true }>('POST', '/auth/change-password', { current_password, new_password }),
  // ─── Usuarios (solo admin) ───
  users: () => get<{ users: AppUser[] }>('/users'),
  createUser: (b: { username: string; password: string; role: Role }) =>
    mutate<AppUser>('POST', '/users', b),
  updateUser: (id: number, b: { role?: Role; active?: boolean; password?: string }) =>
    mutate<AppUser>('PATCH', `/users/${id}`, b),
  deleteUser: (id: number) => mutate<{ ok: true }>('DELETE', `/users/${id}`),
  databases: () => get<{ databases: string[]; default: string }>('/databases'),
  // ─── SFTP ───
  sftpDisk: (path: string) =>
    get<{ path: string; filesystem?: string; size?: string; used?: string; available?: string;
      use_percent?: string; mounted_on?: string; error?: string }>('/sftp/disk', { path }),
  sftpDu: (path: string, top = 20) =>
    get<{ rows: { size: string; path: string }[] }>('/sftp/du', { path, top }),
  sftpOldFiles: (p: { path: string; days: number; pattern: string; max: number }) =>
    get<{ rows: { permissions: string; size: string; modified: string; path: string }[] }>(
      '/sftp/old-files', p),
  getSftp: () =>
    get<SftpCfg>('/settings/sftp'),
  saveSftp: (b: { host?: string; port?: number; user?: string; password?: string; default_path?: string }) =>
    mutate<SftpCfg>('PUT', '/settings/sftp', b),
  testSftp: () => mutate<{ status: string; host?: string; error?: string }>('POST', '/settings/sftp/test'),
  overview: (db: string, fresh = false) => get<OverviewResp>('/overview', { db, fresh }),
  dbSummary: (db: string, fresh = false) =>
    get<{ table_count: number; total_gb: number; skewed: number; database: string | null } & Freshness>(
      '/db_summary',
      { db, fresh },
    ),
  dataslices: (fresh = false) =>
    get<{ rows: Dataslice[] } & Freshness>('/dataslices', { fresh }),
  owners: (db: string, fresh = false) =>
    get<{ rows: OwnerRow[]; database: string | null } & Freshness>('/owners', { db, fresh }),
  tables: (p: { db: string; order: string; page: number; fresh?: boolean; q?: string }) =>
    get<TablesResp>('/tables', { db: p.db, order: p.order, page: p.page, fresh: p.fresh ?? false, q: p.q ?? '' }),
  searchCode: (q: string, db: string) =>
    get<{ rows: { db: string; procedure: string; line: number; snippet: string }[]; q: string; truncated: boolean }>(
      '/search/code', { q, db }),
  tableDetail: (objid: number, table: string) =>
    get<TableDetailResp>('/table', { objid, table }),
  tableSlices: (objid: number) =>
    get<{ slices: { ds: number; gb: number }[]; occupied: number }>('/table/slices', { objid }),
  datasliceTables: (p: { ds: number; page: number; fresh?: boolean; order?: string }) =>
    get<{ rows: DsTableRow[]; has_next: boolean; ds: number; page: number; order: string } & Freshness>(
      '/dataslice/tables',
      { ds: p.ds, page: p.page, fresh: p.fresh ?? false, order: p.order ?? 'ds' },
    ),
  datasliceSummary: (ds: number) =>
    get<{ total: number; skewed: number; ds: number } & Freshness>('/dataslice/summary', { ds }),
  monitoringSpace: () => get<Snapshot<SpaceByDb>>('/monitoring/space'),
  monitoringHealth: () => get<Snapshot<unknown>>('/monitoring/health'),
  monitoringAlerts: () => get<Snapshot<AlertsData>>('/monitoring/alerts'),
  historySpace: () =>
    get<{ points: { at: string; total_gb: number; tables: number }[] }>('/monitoring/history/space'),
  historySaturation: () =>
    get<{ points: { at: string; max_pct: number; alerts: number }[] }>(
      '/monitoring/history/saturation',
    ),
}
