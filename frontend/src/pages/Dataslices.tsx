import { useQuery } from '@tanstack/react-query'
import { useRef } from 'react'

import { FreshnessSeal } from '../components/FreshnessSeal'
import { RefreshButton } from '../components/RefreshButton'
import { api } from '../lib/api'
import { ageFromAt, gb } from '../lib/format'

// color de la barra según saturación (mismos umbrales que las alertas / el DAG)
function barColor(pct: number): string {
  if (pct >= 95) return 'var(--crit)'
  if (pct >= 90) return 'var(--warn)'
  return 'var(--info)'
}

export function Dataslices() {
  const freshRef = useRef(false)
  const q = useQuery({
    queryKey: ['dataslices'],
    queryFn: async () => {
      const fresh = freshRef.current
      freshRef.current = false
      return api.dataslices(fresh)
    },
  })
  const refreshNow = () => {
    freshRef.current = true
    q.refetch()
  }
  const rows = q.data?.rows ?? []
  const maxPct = Math.max(0, ...rows.map((r) => r.pct))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-dense text-lg font-semibold text-ink0">Salud del clúster</h1>
          <p className="text-body text-ink1">Uso por dataslice — saturación física del appliance.</p>
        </div>
        <div className="flex items-center gap-2">
          <FreshnessSeal ageSeconds={ageFromAt(q.data?.at)} />
          <RefreshButton onClick={refreshNow} busy={q.isFetching} />
        </div>
      </div>

      <section className="panel overflow-x-auto">
        <table className="w-full min-w-[560px]">
          <thead>
            <tr className="border-b border-line-strong">
              <th className="th px-3 py-2">Dataslice</th>
              <th className="th px-3 py-2 text-right">Usado</th>
              <th className="th px-3 py-2 text-right">Tamaño</th>
              <th className="th px-3 py-2 text-right">% uso</th>
              <th className="th px-3 py-2">Saturación</th>
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
              <tr key={r.id} className="border-b border-line last:border-0 hover:bg-bg2">
                <td className="px-3 py-1.5 font-data text-body text-ink0">ds {r.id}</td>
                <td className="num px-3 py-1.5 text-body text-ink1">{gb(r.gb_used)}</td>
                <td className="num px-3 py-1.5 text-body text-ink1">{gb(r.gb_size)}</td>
                <td className="num px-3 py-1.5 text-body" style={{ color: barColor(r.pct) }}>
                  {r.pct.toFixed(1)}%
                </td>
                <td className="px-3 py-1.5">
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
    </div>
  )
}
