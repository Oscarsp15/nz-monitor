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
}

export interface OwnerRow {
  owner: string
  tablas: number
  gb: number
}

async function get<T>(path: string, params?: Record<string, string | number | boolean>): Promise<T> {
  const qs = params
    ? '?' +
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== '')
        .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
        .join('&')
    : ''
  const res = await fetch(`/api${path}${qs}`)
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      /* respuesta no-JSON */
    }
    throw new Error(`${res.status} · ${detail}`)
  }
  return res.json() as Promise<T>
}

async function mutate<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      /* respuesta no-JSON */
    }
    throw new Error(`${res.status} · ${detail}`)
  }
  return res.json() as Promise<T>
}

export interface TelegramCfg {
  configured: boolean
  chat_id: string
  has_token: boolean
}

export const api = {
  databases: () => get<{ databases: string[]; default: string }>('/databases'),
  getTelegram: () => get<TelegramCfg>('/settings/telegram'),
  saveTelegram: (b: { bot_token?: string; chat_id?: string }) =>
    mutate<TelegramCfg>('PUT', '/settings/telegram', b),
  testTelegram: () => mutate<{ ok: boolean }>('POST', '/settings/telegram/test'),
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
