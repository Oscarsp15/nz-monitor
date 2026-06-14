import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { FreshnessSeal } from '../components/FreshnessSeal'
import { KpiCard } from '../components/KpiCard'
import { PageSkeleton } from '../components/PageSkeleton'
import { StatusPill } from '../components/StatusPill'
import { TrendPanel } from '../components/TrendChart'
import { api } from '../lib/api'
import { gb, int } from '../lib/format'

export function Overview() {
  const navigate = useNavigate()
  const space = useQuery({ queryKey: ['mon', 'space'], queryFn: api.monitoringSpace })
  const health = useQuery({ queryKey: ['mon', 'health'], queryFn: api.monitoringHealth })
  const alertsQ = useQuery({ queryKey: ['mon', 'alerts'], queryFn: api.monitoringAlerts })
  const ds = useQuery({ queryKey: ['dataslices'], queryFn: () => api.dataslices() })
  const histSpace = useQuery({ queryKey: ['hist', 'space'], queryFn: api.historySpace })
  const histSat = useQuery({ queryKey: ['hist', 'sat'], queryFn: api.historySaturation })

  const dbs = space.data?.data?.databases ?? []
  const totalGb = dbs.reduce((a, d) => a + d.gb, 0)
  const totalTables = dbs.reduce((a, d) => a + d.table_count, 0)
  const maxPct = Math.max(0, ...(ds.data?.rows ?? []).map((r) => r.pct))
  const alertCount = alertsQ.data?.data?.alerts?.length ?? 0

  const spacePts = histSpace.data?.points ?? []
  const spaceVals = spacePts.map((p) => p.total_gb)
  const satPts = histSat.data?.points ?? []
  const satVals = satPts.map((p) => p.max_pct)
  const satLast = satVals[satVals.length - 1] ?? 0
  const satColor = satLast >= 95 ? 'var(--crit)' : satLast >= 90 ? 'var(--warn)' : 'var(--live)'
  const loading =
    space.isLoading ||
    health.isLoading ||
    alertsQ.isLoading ||
    ds.isLoading ||
    histSpace.isLoading ||
    histSat.isLoading

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="font-dense text-lg font-semibold text-ink0">Resumen del clúster</h1>
          <p className="text-body text-ink1">Vigilancia pasiva — datos del recolector.</p>
        </div>
        <FreshnessSeal ageSeconds={space.data?.age_seconds ?? null} />
      </div>

      {loading ? (
        <PageSkeleton kpis={5} panels={2} />
      ) : (
      <div className="reveal space-y-5">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <KpiCard label="Espacio total" value={gb(totalGb)} />
        <KpiCard label="Tablas" value={int(totalTables)} />
        <KpiCard label="Bases" value={int(dbs.length)} />
        <button onClick={() => navigate('/alertas')} className="panel px-4 py-3 text-left">
          <div className="th">Alertas</div>
          <div
            className="mt-1 font-data text-kpi"
            style={{ color: alertCount ? 'var(--crit)' : 'var(--ok)' }}
          >
            {alertsQ.isLoading ? '···' : alertCount}
          </div>
          <div className="mt-0.5 font-data text-micro text-ink2">
            saturación máx. {maxPct ? `${maxPct.toFixed(0)}%` : '—'}
          </div>
        </button>
        <div className="panel px-4 py-3">
          <div className="th">Conexión</div>
          <div className="mt-2">
            <StatusPill status={health.data?.status ?? 'empty'} />
          </div>
          <div className="mt-1 font-data text-micro text-ink2">vigilancia pasiva</div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <TrendPanel
          label="Espacio total · tendencia"
          current={gb(spaceVals[spaceVals.length - 1] ?? totalGb)}
          values={spaceVals}
          color="var(--info)"
          footer={
            spaceVals.length >= 2
              ? `${spaceVals.length} muestras · min ${gb(Math.min(...spaceVals))} · máx ${gb(Math.max(...spaceVals))}`
              : 'se llena conforme el recolector toma muestras'
          }
        />
        <TrendPanel
          label="Saturación máx. dataslice · tendencia"
          current={satVals.length ? `${satLast.toFixed(1)}%` : '—'}
          values={satVals}
          color={satColor}
          footer={
            satVals.length >= 2
              ? `${satVals.length} muestras · min ${Math.min(...satVals).toFixed(1)}% · máx ${Math.max(...satVals).toFixed(1)}%`
              : 'se llena conforme el recolector toma muestras'
          }
        />
      </div>

      {space.data?.status === 'empty' ? (
        <div className="panel px-4 py-8 text-center">
          <p className="text-body text-ink1">Aún no hay datos del recolector.</p>
          <p className="mt-1 font-data text-micro text-ink2">
            Arranca <span className="text-ink1">python -m collector</span> (con VPN) para poblar el
            resumen.
          </p>
        </div>
      ) : (
        <section className="panel overflow-x-auto">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <h2 className="th">Espacio por base de datos</h2>
            <span className="font-data text-micro text-ink2">{dbs.length} bases</span>
          </div>
          <table className="w-full min-w-[520px]">
            <thead>
              <tr className="border-b border-line-strong">
                <th className="th px-4 py-2">Base</th>
                <th className="th px-4 py-2 text-right">Tablas</th>
                <th className="th px-4 py-2 text-right">Espacio</th>
                <th className="th px-4 py-2">Proporción</th>
              </tr>
            </thead>
            <tbody>
              {dbs.map((d) => (
                <tr
                  key={d.db}
                  onClick={() => navigate(`/tablas?db=${encodeURIComponent(d.db)}`)}
                  className="cursor-pointer border-b border-line last:border-0 hover:bg-bg2"
                >
                  <td className="px-4 py-1.5 font-data text-body text-ink0">{d.db}</td>
                  <td className="num px-4 py-1.5 text-body text-ink1">{int(d.table_count)}</td>
                  <td className="num px-4 py-1.5 text-body text-ink0">{gb(d.gb)}</td>
                  <td className="px-4 py-1.5">
                    <span className="block h-1.5 rounded-pill bg-line-strong">
                      <span
                        className="block h-full rounded-pill bg-info"
                        style={{ width: `${totalGb ? (d.gb / totalGb) * 100 : 0}%` }}
                      />
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      </div>
      )}
    </div>
  )
}
