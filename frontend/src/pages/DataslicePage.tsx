import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { ArrowLeft, ChevronLeft, ChevronRight } from 'lucide-react'
import { useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { BlockedHint } from '../components/BlockedHint'
import { ExportButton } from '../components/SearchInput'
import { FreshnessSeal } from '../components/FreshnessSeal'
import { KpiCard } from '../components/KpiCard'
import { PageSkeleton } from '../components/PageSkeleton'
import { RefreshButton } from '../components/RefreshButton'
import { SkewBadge } from '../components/SkewBadge'
import { api, type DsTableRow } from '../lib/api'
import { exportToExcel, stamp } from '../lib/exportXlsx'
import { ageFromAt, gb, int } from '../lib/format'
import { useTableDetailLink } from '../hooks/useTableDetailLink'

export function DataslicePage() {
  const { id } = useParams()
  const ds = Number(id)
  const { open: openDetail, allowed: detailAllowed, blocked: detailBlocked, dismissBlocked } = useTableDetailLink()
  const [page, setPage] = useState(0)
  const [order, setOrder] = useState('ds')
  const freshRef = useRef(false)
  const dsListFreshRef = useRef(false)
  const sumFreshRef = useRef(false)

  const setOrderCol = (col: string) => {
    setOrder(col)
    setPage(0)
  }

  // Estado del dataslice (de la lista, cacheada) para el encabezado.
  const dsList = useQuery({
    queryKey: ['dataslices'],
    queryFn: async () => {
      const fresh = dsListFreshRef.current
      dsListFreshRef.current = false
      return api.dataslices(fresh)
    },
  })
  const info = (dsList.data?.rows ?? []).find((r) => r.id === ds)
  const sum = useQuery({
    queryKey: ['ds-summary', ds],
    queryFn: async () => {
      const fresh = sumFreshRef.current
      sumFreshRef.current = false
      return api.datasliceSummary(ds, fresh)
    },
    enabled: Number.isFinite(ds),
  })

  const q = useQuery({
    queryKey: ['ds-tables', ds, page, order],
    queryFn: async () => {
      const fresh = freshRef.current
      freshRef.current = false
      return api.datasliceTables({ ds, page, fresh, order })
    },
    enabled: Number.isFinite(ds),
    placeholderData: keepPreviousData, // paginación suave (no re-esqueleto al cambiar de página)
  })
  // "Actualizar ahora" debe refrescar TODO lo visible en la página (§2.1/§8): tabla, resumen
  // y el estado del dataslice en el encabezado — no solo las filas.
  const refreshNow = () => {
    freshRef.current = true
    dsListFreshRef.current = true
    sumFreshRef.current = true
    q.refetch()
    dsList.refetch()
    sum.refetch()
  }

  // Carga ATÓMICA + revalidación visible (§2.1/§8/§12).
  const loading = q.isLoading || dsList.isLoading || sum.isLoading
  const updating = q.isFetching || dsList.isFetching || sum.isFetching
  const rows = q.data?.rows ?? []
  const pct = info?.pct ?? 0
  const pctColor = pct >= 95 ? 'var(--crit)' : pct >= 90 ? 'var(--warn)' : 'var(--live)'

  const doExport = () =>
    exportToExcel<DsTableRow>(
      `dataslice_${ds}_${stamp()}.xlsx`,
      rows,
      [
        { header: 'Base', value: (r) => r.db ?? '' },
        { header: 'Tabla', value: (r) => r.table ?? '' },
        { header: 'Owner', value: (r) => r.owner ?? '' },
        { header: 'GB en ds', value: (r) => r.gb_ds },
        { header: 'GB total', value: (r) => r.gb_total },
        { header: 'Skew', value: (r) => r.skew },
      ],
      `ds${ds}`,
    )

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <Link
          to="/dataslices"
          className="tap44 -ml-2 inline-flex items-center gap-1 rounded px-2 font-dense text-label uppercase tracking-wide text-ink1 hover:text-ink0"
        >
          <ArrowLeft size={14} /> Dataslices
        </Link>
        <div className="flex items-center gap-2">
          <FreshnessSeal ageSeconds={ageFromAt(q.data?.at)} updating={updating} />
          <ExportButton onClick={doExport} disabled={rows.length === 0} />
          <div className="hidden lg:block">
            <RefreshButton onClick={refreshNow} busy={updating} />
          </div>
        </div>
      </div>

      <div>
        <h1 className="font-data text-lg text-ink0">Dataslice {ds}</h1>
        <p className="text-body text-ink1">
          Tablas que lo ocupan — las de <span className="text-warn">skew alto</span> son candidatas a
          redistribuir / GROOM.
        </p>
      </div>

      {loading ? (
        <PageSkeleton kpis={4} />
      ) : (
      <div className={`reveal space-y-4 transition-opacity duration-200 ${updating ? 'opacity-50' : ''}`}>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="panel px-4 py-3">
          <div className="th">Saturación</div>
          <div className="mt-1 font-data kpi-value" style={{ color: pctColor }}>
            {info ? `${pct.toFixed(1)}%` : '—'}
          </div>
        </div>
        <KpiCard
          label="Usado / tamaño"
          value={info ? `${gb(info.gb_used)}` : '—'}
          sub={info ? `de ${gb(info.gb_size)}` : undefined}
        />
        <KpiCard label="Tablas en el ds" value={sum.data ? int(sum.data.total) : '—'} loading={sum.isLoading} />
        <div className="panel px-4 py-3">
          <div className="th">Mal distribuidas</div>
          <div
            className="mt-1 font-data kpi-value"
            style={{ color: (sum.data?.skewed ?? 0) > 0 ? 'var(--warn)' : 'var(--ok)' }}
          >
            {sum.isLoading ? '···' : int(sum.data?.skewed)}
          </div>
          <div className="mt-0.5 font-data text-micro text-ink2">skew &gt; 8 · total</div>
        </div>
      </div>

      {/* "Ordenar por" explícito en móvil (<640px, DESIGN §9.3) — mismo estado que el encabezado. */}
      <label className="flex items-center gap-2 font-dense text-label uppercase tracking-wide text-ink1 sm:hidden">
        Ordenar por
        <select
          value={order}
          onChange={(e) => setOrderCol(e.target.value)}
          className="tap44 rounded border border-line bg-bg1 px-2 py-1 font-data text-body text-ink0"
        >
          <option value="ds">GB en ds {ds}</option>
          <option value="total">GB total</option>
          <option value="skew">Skew</option>
        </select>
      </label>

      <BlockedHint show={detailBlocked} onDone={dismissBlocked} />

      {/* Fichas (<640px, DESIGN §9.3). */}
      <div className="space-y-2 sm:hidden">
        {q.isError && (
          <div className="panel px-4 py-8 text-center text-body text-crit">
            {(q.error as Error).message}
            <div className="mt-1 font-data text-micro text-ink2">¿VPN activa?</div>
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
                {r.db} · {r.owner}
              </div>
              <div className="mt-2 flex items-center justify-between gap-3">
                <div>
                  <div className="th">GB en ds {ds}</div>
                  <div className="num text-body text-ink0">{gb(r.gb_ds)}</div>
                </div>
                <SkewBadge skew={r.skew} />
              </div>
            </div>
          ))}
        {!q.isError && !loading && rows.length === 0 && (
          <div className="panel px-4 py-8 text-center text-body text-ink2">Sin tablas en este dataslice.</div>
        )}
      </div>

      {/* Tabla (≥640px): completa desde 1024px; 640–1023px oculta GB total y Owner (§9.3). */}
      <section className="panel hidden overflow-x-auto sm:block">
        <table className="w-full min-w-[520px]">
          <thead>
            <tr className="border-b border-line-strong">
              <th className="th px-3 py-2">Tabla</th>
              <th className="th px-3 py-2">Base</th>
              <th className="hidden px-3 py-2 lg:table-cell th">Owner</th>
              <th
                onClick={() => setOrderCol('ds')}
                className={`th cursor-pointer select-none px-3 py-2 text-right hover:text-ink0 ${order === 'ds' ? 'text-ink0' : ''}`}
              >
                GB en ds {ds}
                {order === 'ds' && <span className="ml-1 text-live">▾</span>}
              </th>
              <th
                onClick={() => setOrderCol('total')}
                className={`th hidden cursor-pointer select-none px-3 py-2 text-right hover:text-ink0 lg:table-cell ${order === 'total' ? 'text-ink0' : ''}`}
              >
                GB total
                {order === 'total' && <span className="ml-1 text-live">▾</span>}
              </th>
              <th
                onClick={() => setOrderCol('skew')}
                className={`th cursor-pointer select-none px-3 py-2 text-right hover:text-ink0 ${order === 'skew' ? 'text-ink0' : ''}`}
              >
                Skew
                {order === 'skew' && <span className="ml-1 text-live">▾</span>}
              </th>
            </tr>
          </thead>
          <tbody>
            {q.isError && (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-body text-crit">
                  {(q.error as Error).message}
                  <div className="mt-1 font-data text-micro text-ink2">¿VPN activa?</div>
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
                  <td className="hidden px-3 py-1.5 font-data text-body text-ink1 lg:table-cell">{r.owner}</td>
                  <td className="num px-3 py-1.5 text-body text-ink0">{gb(r.gb_ds)}</td>
                  <td className="num hidden px-3 py-1.5 text-body text-ink1 lg:table-cell">{gb(r.gb_total)}</td>
                  <td className="px-3 py-1.5">
                    <SkewBadge skew={r.skew} />
                  </td>
                </tr>
              ))}
            {!q.isError && !loading && rows.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-body text-ink2">
                  Sin tablas en este dataslice.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

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

      <div className="flex justify-center border-t border-line pt-4 lg:hidden">
        <RefreshButton onClick={refreshNow} busy={updating} />
      </div>
      </div>
      )}
    </div>
  )
}
