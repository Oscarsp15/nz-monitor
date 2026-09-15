import { useQuery } from '@tanstack/react-query'
import { useRef } from 'react'

import { useNavigate } from 'react-router-dom'

import { ExportButton } from '../components/SearchInput'
import { FreshnessSeal } from '../components/FreshnessSeal'
import { KpiCard } from '../components/KpiCard'
import { PageSkeleton } from '../components/PageSkeleton'
import { RefreshButton } from '../components/RefreshButton'
import { TrendPanel } from '../components/TrendChart'
import { api, type Dataslice } from '../lib/api'
import { exportToExcel, stamp } from '../lib/exportXlsx'
import { ageFromAt, gb } from '../lib/format'

// color de la barra según saturación (mismos umbrales que las alertas / el DAG)
function barColor(pct: number): string {
  if (pct >= 95) return 'var(--crit)'
  if (pct >= 90) return 'var(--warn)'
  return 'var(--info)'
}

export function Dataslices() {
  const navigate = useNavigate()
  const freshRef = useRef(false)
  const q = useQuery({
    queryKey: ['dataslices'],
    queryFn: async () => {
      const fresh = freshRef.current
      freshRef.current = false
      return api.dataslices(fresh)
    },
  })
  const histSat = useQuery({ queryKey: ['hist', 'sat'], queryFn: api.historySaturation })
  const refreshNow = () => {
    freshRef.current = true
    q.refetch()
  }
  // Carga ATÓMICA + revalidación visible (§2.1/§8/§12).
  const loading = q.isLoading || histSat.isLoading
  const updating = q.isFetching || histSat.isFetching
  const rows = q.data?.rows ?? []
  const maxPct = Math.max(0, ...rows.map((r) => r.pct))
  const avgPct = rows.length ? rows.reduce((a, r) => a + r.pct, 0) / rows.length : 0
  const usedGb = rows.reduce((a, r) => a + r.gb_used, 0)

  const doExport = () =>
    exportToExcel<Dataslice>(
      `dataslices_${stamp()}.xlsx`,
      rows,
      [
        { header: 'Dataslice', value: (r) => r.id },
        { header: '% uso', value: (r) => r.pct },
        { header: 'Usado GB', value: (r) => r.gb_used },
        { header: 'Tamaño GB', value: (r) => r.gb_size },
        { header: 'Estado', value: (r) => r.status },
      ],
      'Dataslices',
    )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-dense text-lg font-semibold text-ink0">Salud del clúster</h1>
          <p className="text-body text-ink1">Uso por dataslice — saturación física del appliance.</p>
        </div>
        <div className="flex items-center gap-2">
          <FreshnessSeal ageSeconds={ageFromAt(q.data?.at)} updating={updating} />
          <ExportButton onClick={doExport} disabled={rows.length === 0} />
          <div className="hidden lg:block">
            <RefreshButton onClick={refreshNow} busy={updating} />
          </div>
        </div>
      </div>

      {loading ? (
        <PageSkeleton kpis={4} panels={2} />
      ) : (
      <div className={`reveal space-y-4 transition-opacity duration-200 ${updating ? 'opacity-50' : ''}`}>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Dataslices" value={String(rows.length)} />
        <KpiCard label="Saturación máx" value={`${maxPct.toFixed(1)}%`} />
        <KpiCard label="Saturación prom" value={`${avgPct.toFixed(1)}%`} />
        <KpiCard label="Usado total" value={gb(usedGb)} />
      </div>

      <TrendPanel
        label="Saturación máx. · tendencia"
        current={`${maxPct.toFixed(1)}%`}
        values={(histSat.data?.points ?? []).map((p) => p.max_pct)}
        color={maxPct >= 95 ? 'var(--crit)' : maxPct >= 90 ? 'var(--warn)' : 'var(--live)'}
      />

      {/* Fichas (<640px, DESIGN §9.3). */}
      <div className="space-y-2 sm:hidden">
        {q.isError && (
          <div className="panel px-4 py-8 text-center text-body text-crit">
            {(q.error as Error).message}
            <div className="mt-1 font-data text-micro text-ink2">¿VPN activa?</div>
          </div>
        )}
        {rows.map((r) => (
          <div
            key={r.id}
            role="button"
            tabIndex={0}
            onClick={() => navigate(`/dataslice/${r.id}`)}
            onKeyDown={(e) => e.key === 'Enter' && navigate(`/dataslice/${r.id}`)}
            className="tap44-row panel cursor-pointer px-4 py-3 active:bg-bg2"
          >
            <div className="flex items-center justify-between">
              <span className="font-data text-body text-ink0">ds {r.id}</span>
              <span className="font-data text-body" style={{ color: barColor(r.pct) }}>
                {r.pct.toFixed(1)}%
              </span>
            </div>
            <span className="mt-2 block h-1.5 w-full rounded-pill bg-line-strong">
              <span
                className="block h-full rounded-pill"
                style={{ width: `${r.pct}%`, background: barColor(r.pct) }}
              />
            </span>
            <div className="mt-2 flex items-center justify-between gap-3">
              <div>
                <div className="th">Usado / tamaño</div>
                <div className="num text-body text-ink0">
                  {gb(r.gb_used)} <span className="text-ink2">de {gb(r.gb_size)}</span>
                </div>
              </div>
              <div className="font-data text-micro text-ink1">{r.status}</div>
            </div>
          </div>
        ))}
        {!q.isError && !q.isLoading && rows.length === 0 && (
          <div className="panel px-4 py-8 text-center text-body text-ink2">Sin dataslices.</div>
        )}
      </div>

      <section className="panel hidden overflow-x-auto sm:block">
        <table className="w-full min-w-[440px]">
          <thead>
            <tr className="border-b border-line-strong">
              <th className="th px-3 py-2">Dataslice</th>
              <th className="th px-3 py-2 text-right">% uso</th>
              <th className="th px-3 py-2 text-right">Usado</th>
              <th className="hidden px-3 py-2 text-right lg:table-cell th">Tamaño</th>
              <th className="hidden px-3 py-2 lg:table-cell th">Saturación</th>
              <th className="th px-3 py-2">Estado</th>
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
            {rows.map((r) => (
              <tr
                key={r.id}
                onClick={() => navigate(`/dataslice/${r.id}`)}
                className="tap44-row cursor-pointer border-b border-line last:border-0 hover:bg-bg2"
              >
                <td className="px-3 py-1.5 font-data text-body text-ink0">ds {r.id}</td>
                <td className="num px-3 py-1.5 text-body" style={{ color: barColor(r.pct) }}>
                  {r.pct.toFixed(1)}%
                </td>
                <td className="num px-3 py-1.5 text-body text-ink1">{gb(r.gb_used)}</td>
                <td className="num hidden px-3 py-1.5 text-body text-ink1 lg:table-cell">{gb(r.gb_size)}</td>
                <td className="hidden px-3 py-1.5 lg:table-cell">
                  <span className="block h-1.5 w-full rounded-pill bg-line-strong">
                    <span
                      className="block h-full rounded-pill"
                      style={{ width: `${r.pct}%`, background: barColor(r.pct) }}
                    />
                  </span>
                </td>
                <td className="px-3 py-1.5 font-data text-micro text-ink1">{r.status}</td>
              </tr>
            ))}
            {!q.isError && !q.isLoading && rows.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-body text-ink2">
                  Sin dataslices.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      {rows.length > 0 && (
        <p className="font-data text-micro text-ink2">
          Saturación máxima del clúster: <span style={{ color: barColor(maxPct) }}>{maxPct.toFixed(1)}%</span>
        </p>
      )}

      <div className="flex justify-center border-t border-line pt-4 lg:hidden">
        <RefreshButton onClick={refreshNow} busy={updating} />
      </div>
      </div>
      )}
    </div>
  )
}
