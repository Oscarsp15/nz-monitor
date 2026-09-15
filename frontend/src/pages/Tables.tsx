import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { BlockedHint } from '../components/BlockedHint'
import { ExportButton, SearchInput } from '../components/SearchInput'
import { FreshnessSeal } from '../components/FreshnessSeal'
import { KpiCard } from '../components/KpiCard'
import { PageSkeleton } from '../components/PageSkeleton'
import { RefreshButton } from '../components/RefreshButton'
import { SkewBadge } from '../components/SkewBadge'
import { api, type TableRow } from '../lib/api'
import { exportToExcel, stamp } from '../lib/exportXlsx'
import { ageFromAt, gb, int } from '../lib/format'
import { useDebounced } from '../hooks/useDebounced'
import { useLiveMode } from '../hooks/useLiveMode'
import { useTableDetailLink } from '../hooks/useTableDetailLink'

// `priority` = orden de preferencia en 640–1023px (DESIGN §9.3): TABLA > ESPACIO > SKEW > BASE >
// ESQUEMA > OWNER > DISTRIBUCIÓN. Las de priority > 4 se ocultan en tablet, no se encoge la letra.
const COLS: { key: string; label: string; order?: string; num?: boolean; priority: number }[] = [
  { key: 'table', label: 'Tabla', priority: 1 },
  { key: 'db', label: 'Base', priority: 4 },
  { key: 'schema', label: 'Esquema', priority: 5 },
  { key: 'owner', label: 'Owner', priority: 6 },
  { key: 'distribute_on', label: 'Distribución', priority: 7 },
  { key: 'space_gb', label: 'Espacio', order: 'space', num: true, priority: 2 },
  { key: 'skew', label: 'Skew', order: 'skew', num: true, priority: 3 },
]
const SORT_OPTIONS = [
  { value: 'space', label: 'Espacio' },
  { value: 'skew', label: 'Skew' },
]

export function Tables() {
  const { open: openDetail, allowed: detailAllowed, blocked: detailBlocked, dismissBlocked } = useTableDetailLink()
  const [sp, setSp] = useSearchParams()
  const dbsQ = useQuery({ queryKey: ['databases'], queryFn: api.databases })

  const db = sp.get('db') || '*'
  const [order, setOrder] = useState('space')
  const [page, setPage] = useState(0)
  const [searchRaw, setSearchRaw] = useState('')
  const search = useDebounced(searchRaw.trim())
  const freshRef = useRef(false)
  const summaryFreshRef = useRef(false)

  const setDb = (value: string) => {
    setSp(value === '*' ? {} : { db: value })
    setPage(0)
  }

  const q = useQuery({
    queryKey: ['tables', db, order, page, search],
    queryFn: async () => {
      const fresh = freshRef.current
      freshRef.current = false
      return api.tables({ db, order, page, fresh, q: search })
    },
    placeholderData: keepPreviousData, // paginación/búsqueda suave (sin re-esqueleto)
  })

  const summary = useQuery({
    queryKey: ['dbsummary', db],
    queryFn: async () => {
      const fresh = summaryFreshRef.current
      summaryFreshRef.current = false
      return api.dbSummary(db, fresh)
    },
    placeholderData: keepPreviousData,
  })

  // "Actualizar ahora" debe refrescar TODO (AGENTS §2.1/§8): filas Y KPIs, no solo la tabla.
  const refreshNow = () => {
    freshRef.current = true
    summaryFreshRef.current = true
    q.refetch()
    summary.refetch()
  }
  const { live, setLive, allowed: liveAllowed } = useLiveMode(refreshNow)

  const setOrderCol = (col?: string) => {
    if (!col) return
    setOrder(col)
    setPage(0)
  }

  // Carga ATÓMICA (§8/§12): sin dato previo → esqueleto. Con dato previo → se pinta atenuado
  // y marcado "actualizando…" mientras cualquiera de las consultas dependientes está en vuelo
  // (isFetching, no solo isLoading — así KPIs y filas revelan el nuevo valor juntos, nunca
  // escalonados, aunque cada query resuelva en un instante distinto).
  const loading = q.isLoading || summary.isLoading || dbsQ.isLoading
  const updating = q.isFetching || summary.isFetching || dbsQ.isFetching
  const rows = q.data?.rows ?? []

  const doExport = () => {
    exportToExcel<TableRow>(
      `tablas_${db === '*' ? 'todas' : db}_${stamp()}.xlsx`,
      rows,
      [
        { header: 'Base', value: (r) => r.db ?? '' },
        { header: 'Esquema', value: (r) => r.schema ?? '' },
        { header: 'Tabla', value: (r) => r.table ?? '' },
        { header: 'Owner', value: (r) => r.owner ?? '' },
        { header: 'Distribución', value: (r) => r.distribute_on },
        { header: 'Espacio GB', value: (r) => r.space_gb },
        { header: 'Skew', value: (r) => r.skew },
      ],
      'Tablas',
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-dense text-lg font-semibold text-ink0">Tablas y distribución</h1>
          <p className="text-body text-ink1">
            Investigación en vivo — skew = concentración en su dataslice más cargado.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <FreshnessSeal ageSeconds={ageFromAt(q.data?.at)} live={live} updating={updating} />
          {/* En escritorio, alcanzar el botón arriba a la derecha es normal (ratón). En móvil/
              tablet se oculta aquí y reaparece al alcance del pulgar, al pie del contenido
              (DESIGN §9.2). */}
          <div className="hidden lg:block">
            <RefreshButton onClick={refreshNow} busy={updating} />
          </div>
        </div>
      </div>

      {loading ? (
        <PageSkeleton kpis={3} />
      ) : (
      <div className={`reveal space-y-4 transition-opacity duration-200 ${updating ? 'opacity-50' : ''}`}>
      {/* Dashboard de la base seleccionada */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <KpiCard
          label={db === '*' ? 'Tablas (todas)' : `Tablas · ${db}`}
          value={int(summary.data?.table_count)}
          loading={summary.isLoading}
        />
        <KpiCard label="Espacio total" value={gb(summary.data?.total_gb)} loading={summary.isLoading} />
        <div className="panel px-4 py-3">
          <div className="th">Mal distribuidas</div>
          <div
            className="mt-1 font-data kpi-value"
            style={{ color: (summary.data?.skewed ?? 0) > 0 ? 'var(--warn)' : 'var(--ok)' }}
          >
            {summary.isLoading ? '···' : int(summary.data?.skewed)}
          </div>
          <div className="mt-0.5 font-data text-micro text-ink2">skew &gt; 8</div>
        </div>
      </div>

      {/* Controles */}
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 font-dense text-label uppercase tracking-wide text-ink1">
          Base
          <select
            value={db}
            onChange={(e) => setDb(e.target.value)}
            className="tap44 rounded border border-line bg-bg1 px-2 py-1 font-data text-body text-ink0"
          >
            <option value="*">Todas</option>
            {dbsQ.data?.databases.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <SearchInput
          value={searchRaw}
          onChange={(v) => {
            setSearchRaw(v)
            setPage(0)
          }}
          placeholder="Tabla u owner…"
        />
        <ExportButton onClick={doExport} disabled={rows.length === 0} />
        {/* "Ordenar por" explícito en móvil (<640px, DESIGN §9.3): sin encabezados donde pulsar,
            usa el mismo estado que el clic en el encabezado. */}
        <label className="flex items-center gap-2 font-dense text-label uppercase tracking-wide text-ink1 sm:hidden">
          Ordenar por
          <select
            value={order}
            onChange={(e) => setOrderCol(e.target.value)}
            className="tap44 rounded border border-line bg-bg1 px-2 py-1 font-data text-body text-ink0"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        <label
          className={`ml-auto hidden items-center gap-2 font-dense text-label uppercase tracking-wide text-ink1 lg:flex ${
            liveAllowed ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'
          }`}
          title={liveAllowed ? undefined : 'Tu rol no permite consultas en vivo'}
        >
          <input
            type="checkbox"
            checked={live}
            disabled={!liveAllowed}
            onChange={(e) => setLive(e.target.checked)}
            className="tap44 accent-[var(--live)]"
          />
          Modo en vivo
        </label>
      </div>

      <BlockedHint show={detailBlocked} onDone={dismissBlocked} />

      {/* Fichas (<640px, DESIGN §9.3): nunca scroll horizontal de 7 columnas con una mano. */}
      <div className="space-y-2 sm:hidden">
        {q.isError && (
          <div className="panel px-4 py-8 text-center text-body text-crit">
            {(q.error as Error).message}
            <div className="mt-1 font-data text-micro text-ink2">
              ¿Conectado a la VPN? Netezza solo responde desde la red interna.
            </div>
          </div>
        )}
        {!q.isError &&
          rows.map((r) => (
            <div
              key={r.objid}
              role="button"
              tabIndex={0}
              onClick={() => openDetail(r.objid, r.table)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') openDetail(r.objid, r.table)
              }}
              title={detailAllowed ? undefined : 'Tu rol no permite consultas en vivo'}
              aria-disabled={!detailAllowed}
              className={`tap44-row panel px-4 py-3 ${detailAllowed ? 'cursor-pointer active:bg-bg2' : 'cursor-not-allowed opacity-70'}`}
            >
              <div className="break-all font-data text-body text-ink0">{r.table}</div>
              <div className="mt-0.5 truncate font-dense text-label text-ink2">
                {r.db} · {r.schema} · {r.owner}
              </div>
              <div className="mt-2 flex items-center justify-between gap-3">
                <div>
                  <div className="th">Espacio</div>
                  <div className="num text-body text-ink0">{gb(r.space_gb)}</div>
                </div>
                <SkewBadge skew={r.skew} />
              </div>
            </div>
          ))}
        {!q.isError && !q.isLoading && rows.length === 0 && (
          <div className="panel px-4 py-8 text-center text-body text-ink2">Sin resultados.</div>
        )}
      </div>

      {/* Tabla (≥640px): completa desde 1024px; 640–1023px oculta columnas de menor prioridad
          (§9.3), nunca encoge la letra. */}
      <section className="panel hidden overflow-x-auto sm:block">
        <table className="w-full min-w-[520px]">
          <thead>
            <tr className="border-b border-line-strong">
              {COLS.map((c) => (
                <th
                  key={c.key}
                  onClick={() => setOrderCol(c.order)}
                  className={`th px-3 py-2 ${c.num ? 'text-right' : ''} ${
                    c.order ? 'cursor-pointer select-none hover:text-ink0' : ''
                  } ${order === c.order ? 'text-ink0' : ''} ${c.priority > 4 ? 'hidden lg:table-cell' : ''}`}
                >
                  {c.label}
                  {order === c.order && <span className="ml-1 text-live">▾</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {q.isError && (
              <tr>
                <td colSpan={COLS.length} className="px-3 py-8 text-center text-body text-crit">
                  {(q.error as Error).message}
                  <div className="mt-1 font-data text-micro text-ink2">
                    ¿Conectado a la VPN? Netezza solo responde desde la red interna.
                  </div>
                </td>
              </tr>
            )}
            {!q.isError &&
              rows.map((r) => (
                <tr
                  key={r.objid}
                  onClick={() => openDetail(r.objid, r.table)}
                  title={detailAllowed ? undefined : 'Tu rol no permite consultas en vivo'}
                  aria-disabled={!detailAllowed}
                  className={`tap44-row border-b border-line last:border-0 ${detailAllowed ? 'cursor-pointer hover:bg-bg2' : 'cursor-not-allowed opacity-70'}`}
                >
                  <td className="px-3 py-1.5 font-data text-body text-ink0">{r.table}</td>
                  <td className="px-3 py-1.5 font-data text-body text-ink1">{r.db}</td>
                  <td className="hidden px-3 py-1.5 font-data text-body text-ink1 lg:table-cell">{r.schema}</td>
                  <td className="hidden px-3 py-1.5 font-data text-body text-ink1 lg:table-cell">{r.owner}</td>
                  <td className="hidden px-3 py-1.5 font-data text-micro text-ink1 lg:table-cell">{r.distribute_on}</td>
                  <td className="num px-3 py-1.5 text-body text-ink0">{gb(r.space_gb)}</td>
                  <td className="px-3 py-1.5">
                    <SkewBadge skew={r.skew} />
                  </td>
                </tr>
              ))}
            {!q.isError && !q.isLoading && rows.length === 0 && (
              <tr>
                <td colSpan={COLS.length} className="px-3 py-8 text-center text-body text-ink2">
                  Sin resultados.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      {/* Paginación */}
      <div className="flex items-center justify-end gap-2">
        <button
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          disabled={page === 0 || q.isFetching}
          className="tap44 flex items-center justify-center rounded border border-line text-ink1 hover:bg-bg2 disabled:opacity-40"
          aria-label="Anterior"
        >
          <ChevronLeft size={16} />
        </button>
        <span className="font-data text-micro text-ink2">página {page + 1}</span>
        <button
          onClick={() => setPage((p) => p + 1)}
          disabled={!q.data?.has_next || q.isFetching}
          className="tap44 flex items-center justify-center rounded border border-line text-ink1 hover:bg-bg2 disabled:opacity-40"
          aria-label="Siguiente"
        >
          <ChevronRight size={16} />
        </button>
      </div>

      {/* Alcanzable con el pulgar en móvil/tablet (DESIGN §9.2): "Actualizar ahora" y "Modo en
          vivo" repetidos al pie del contenido, no solo arriba a la derecha. */}
      <div className="flex flex-wrap items-center justify-center gap-4 border-t border-line pt-4 lg:hidden">
        <RefreshButton onClick={refreshNow} busy={updating} />
        <label
          className={`flex items-center gap-2 font-dense text-label uppercase tracking-wide text-ink1 ${
            liveAllowed ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'
          }`}
          title={liveAllowed ? undefined : 'Tu rol no permite consultas en vivo'}
        >
          <input
            type="checkbox"
            checked={live}
            disabled={!liveAllowed}
            onChange={(e) => setLive(e.target.checked)}
            className="tap44 accent-[var(--live)]"
          />
          Modo en vivo
        </label>
      </div>
      </div>
      )}
    </div>
  )
}
