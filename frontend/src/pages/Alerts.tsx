import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, ShieldCheck } from 'lucide-react'

import { FreshnessSeal } from '../components/FreshnessSeal'
import { api, type AlertItem } from '../lib/api'

const COLOR = { warn: 'var(--warn)', crit: 'var(--crit)' } as const

function Row({ a }: { a: AlertItem }) {
  const c = COLOR[a.level]
  return (
    <div
      className="flex items-center gap-3 border-b border-line px-4 py-2.5 last:border-0"
      style={{ borderLeft: `2px solid ${c}` }}
    >
      <AlertTriangle size={15} strokeWidth={1.8} style={{ color: c }} />
      <span className="flex-1 text-body text-ink0">{a.message}</span>
      <span className="num text-body" style={{ color: c }}>
        {a.value}%
      </span>
    </div>
  )
}

export function Alerts() {
  const q = useQuery({ queryKey: ['mon', 'alerts'], queryFn: api.monitoringAlerts })
  const data = q.data?.data
  const alerts = data?.alerts ?? []

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-dense text-lg font-semibold text-ink0">Alertas</h1>
          <p className="text-body text-ink1">Dataslices cerca de llenarse (≥90% atención · ≥95% crítico).</p>
        </div>
        <FreshnessSeal ageSeconds={q.data?.age_seconds ?? null} />
      </div>

      {q.data?.status === 'empty' ? (
        <div className="panel px-4 py-8 text-center text-body text-ink1">
          Aún no hay datos del recolector.
        </div>
      ) : alerts.length === 0 ? (
        <div className="panel flex items-center justify-center gap-2 px-4 py-10">
          <ShieldCheck size={18} className="text-ok" />
          <span className="text-body text-ink1">Sin alertas. Clúster saludable.</span>
        </div>
      ) : (
        <section className="panel overflow-hidden">
          <div className="border-b border-line px-4 py-2.5">
            <h2 className="th">
              {alerts.length} alerta{alerts.length === 1 ? '' : 's'} · saturación máx.{' '}
              {data?.max_dataslice_pct}%
            </h2>
          </div>
          {alerts.map((a, i) => (
            <Row key={i} a={a} />
          ))}
        </section>
      )}
    </div>
  )
}
