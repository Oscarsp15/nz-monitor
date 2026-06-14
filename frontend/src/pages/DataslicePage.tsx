import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { ArrowLeft, ChevronLeft, ChevronRight } from 'lucide-react'
import { useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { ExportButton } from '../components/SearchInput'
import { KpiCard } from '../components/KpiCard'
import { PageSkeleton } from '../components/PageSkeleton'
import { RefreshButton } from '../components/RefreshButton'
import { SkewBadge } from '../components/SkewBadge'
import { api, type DsTableRow } from '../lib/api'
import { exportToExcel, stamp } from '../lib/exportXlsx'
import { gb } from '../lib/format'

export function DataslicePage() {
  const { id } = useParams()
  const ds = Number(id)
  const navigate = useNavigate()
  const [page, setPage] = useState(0)
  const freshRef = useRef(false)

  // Estado del dataslice (de la lista, cacheada) para el encabezado.
  const dsList = useQuery({ queryKey: ['dataslices'], queryFn: () => api.dataslices() })
  const info = (dsList.data?.rows ?? []).find((r) => r.id === ds)
  const sum = useQuery({
    queryKey: ['ds-summary', ds],
    queryFn: () => api.datasliceSummary(ds),
    enabled: Number.isFinite(ds),
  })

  const q = useQuery({
    queryKey: ['ds-tables', ds, page],
    queryFn: async () => {
      const fresh = freshRef.current
      freshRef.current = false
      return api.datasliceTables({ ds, page, fresh })
    },
    enabled: Number.isFinite(ds),
    placeholderData: keepPreviousData, // paginación suave (no re-esqueleto al cambiar de página)
  })
  const refreshNow = () => {
    freshRef.current = true
    q.refetch()
  }

  // Carga ATÓMICA: esqueleto hasta que TODAS las consultas de primer carga terminen.
  const loading = q.isLoading || dsList.isLoading || sum.isLoading
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
          className="inline-flex items-center gap-1 font-dense text-label uppercase tracking-wide text-ink1 hover:text-ink0"
        >
          <ArrowLeft size={14} /> Dataslices
        </Link>
        <div className="flex items-center gap-2">
          <ExportButton onClick={doExport} disabled={rows.length === 0} />
          <RefreshButton onClick={refreshNow} busy={q.isFetching} />
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
      <div className="reveal space-y-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="panel px-4 py-3">
          <div className="th">Saturación</div>
          <div className="mt-1 font-data text-kpi" style={{ color: pctColor }}>
            {info ? `${pct.toFixed(1)}%` : '—'}
          </div>
        </div>
        <KpiCard
          label="Usado / tamaño"
          value={info ? `${gb(info.gb_used)}` : '—'}
          sub={info ? `de ${gb(info.gb_size)}` : undefined}
        />
        <KpiCard label="Tablas en el ds" value={String(sum.data?.total ?? '—')} loading={sum.isLoading} />
        <div className="panel px-4 py-3">
          <div className="th">Mal distribuidas</div>
          <div
            className="mt-1 font-data text-kpi"
            style={{ color: (sum.data?.skewed ?? 0) > 0 ? 'var(--warn)' : 'var(--ok)' }}
          >
            {sum.isLoading ? '···' : (sum.data?.skewed ?? 0)}
          </div>
          <div className="mt-0.5 font-data text-micro text-ink2">skew &gt; 8 · total</div>
        </div>
      </div>

      <section className="panel overflow-x-auto">
        <table className="w-full min-w-[680px]">
          <thead>
            <tr className="border-b border-line-strong">
              <th className="th px-3 py-2">Tabla</th>
              <th className="th px-3 py-2">Base</th>
              <th className="th px-3 py-2">Owner</th>
              <th className="th px-3 py-2 text-right">GB en ds {ds}</th>
              <th className="th px-3 py-2 text-right">GB total</th>
              <th className="th px-3 py-2 text-right">Skew</th>
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
                  onClick={() =>
                    navigate(`/tabla/${r.objid}?name=${encodeURIComponent(r.table ?? '')}`)
                  }
                  className="cursor-pointer border-b border-line last:border-0 hover:bg-bg2"
                >
                  <td className="px-3 py-1.5 font-data text-body text-ink0">{r.table}</td>
                  <td className="px-3 py-1.5 font-data text-body text-ink1">{r.db}</td>
                  <td className="px-3 py-1.5 font-data text-body text-ink1">{r.owner}</td>
                  <td className="num px-3 py-1.5 text-body text-ink0">{gb(r.gb_ds)}</td>
                  <td className="num px-3 py-1.5 text-body text-ink1">{gb(r.gb_total)}</td>
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
          className="rounded border border-line p-1 text-ink1 hover:bg-bg2 disabled:opacity-40"
          aria-label="Anterior"
        >
          <ChevronLeft size={16} />
        </button>
        <span className="font-data text-micro text-ink2">página {page + 1}</span>
        <button
          onClick={() => setPage((p) => p + 1)}
          disabled={!q.data?.has_next || q.isFetching}
          className="rounded border border-line p-1 text-ink1 hover:bg-bg2 disabled:opacity-40"
          aria-label="Siguiente"
        >
          <ChevronRight size={16} />
        </button>
      </div>
      </div>
      )}
    </div>
  )
}
