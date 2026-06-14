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
  gb_ds: number
}

export interface TablesResp extends Freshness {
  rows: TableRow[]
  has_next: boolean
  database: string | null
  ds: number
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

export const api = {
  databases: () => get<{ databases: string[]; default: string }>('/databases'),
  overview: (db: string, fresh = false) => get<OverviewResp>('/overview', { db, fresh }),
  dataslices: (fresh = false) =>
    get<{ rows: Dataslice[] } & Freshness>('/dataslices', { fresh }),
  tables: (p: { db: string; ds: number; order: string; page: number; fresh?: boolean }) =>
    get<TablesResp>('/tables', { ...p, fresh: p.fresh ?? false }),
  tableDetail: (objid: number, table: string) =>
    get<TableDetailResp>('/table', { objid, table }),
  tableSlices: (objid: number) =>
    get<{ slices: { ds: number; gb: number }[] }>('/table/slices', { objid }),
  monitoringSpace: () => get<Snapshot<SpaceByDb>>('/monitoring/space'),
  monitoringHealth: () => get<Snapshot<unknown>>('/monitoring/health'),
}
