import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import { KpiCard } from '../components/KpiCard'
import { api } from '../lib/api'
import { gb } from '../lib/format'

export function TableDetail() {
  const { objid } = useParams()
  const id = Number(objid)
  const [sp] = useSearchParams()
  const name = sp.get('name') ?? ''

  const detail = useQuery({
    queryKey: ['table', id],
    queryFn: () => api.tableDetail(id, name),
    enabled: Number.isFinite(id),
  })
  const slices = useQuery({
    queryKey: ['slices', id],
    queryFn: () => api.tableSlices(id),
    enabled: Number.isFinite(id),
  })

  const meta = detail.data?.meta
  const maxGb = Math.max(0, ...(slices.data?.slices ?? []).map((s) => s.gb))

  return (
    <div className="space-y-5">
      <Link
        to="/tablas"
        className="inline-flex items-center gap-1 font-dense text-label uppercase tracking-wide text-ink1 hover:text-ink0"
      >
        <ArrowLeft size={14} /> Volver
      </Link>

      <div>
        <h1 className="font-data text-lg text-ink0">{name || `objid ${id}`}</h1>
        {meta && (
          <p className="font-data text-micro text-ink2">
            {meta.db}.{meta.sch} · owner {meta.owner} · creada {meta.created}
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        <KpiCard label="Espacio" value={gb(meta?.gb)} loading={detail.isLoading} />
        <KpiCard label="Skew" value={meta ? meta.skew.toFixed(2) : '—'} loading={detail.isLoading} />
        <KpiCard
          label="Dataslices ocupados"
          value={String(slices.data?.slices.length ?? '—')}
          loading={slices.isLoading}
        />
      </div>

      {/* Dataslices que ocupa */}
      <section className="panel overflow-hidden">
        <div className="border-b border-line px-4 py-2.5">
          <h2 className="th">Dataslices que ocupa</h2>
        </div>
        <div className="space-y-1 p-3">
          {(slices.data?.slices ?? []).map((s) => (
            <div key={s.ds} className="flex items-center gap-3">
              <span className="num w-14 text-micro text-ink2">ds {s.ds}</span>
              <span className="block h-2 flex-1 rounded-pill bg-line-strong">
                <span
                  className="block h-full rounded-pill bg-info"
                  style={{ width: `${maxGb ? (s.gb / maxGb) * 100 : 0}%` }}
                />
              </span>
              <span className="num w-20 text-micro text-ink1">{gb(s.gb)}</span>
            </div>
          ))}
          {slices.isError && (
            <p className="px-1 py-4 text-center text-body text-crit">
              No se pudo consultar (¿VPN activa?).
            </p>
          )}
        </div>
      </section>

      {/* Última actividad */}
      <section className="panel overflow-x-auto">
        <div className="border-b border-line px-4 py-2.5">
          <h2 className="th">Última actividad</h2>
        </div>
        <table className="w-full min-w-[640px]">
          <thead>
            <tr className="border-b border-line-strong">
              <th className="th px-3 py-2">Cuándo</th>
              <th className="th px-3 py-2">Acción</th>
              <th className="th px-3 py-2">Usuario</th>
              <th className="th px-3 py-2">SQL</th>
            </tr>
          </thead>
          <tbody>
            {(detail.data?.history ?? []).map((h, i) => (
              <tr key={i} className="border-b border-line last:border-0 hover:bg-bg2">
                <td className="px-3 py-1.5 font-data text-micro text-ink1">{h.tend}</td>
                <td className="px-3 py-1.5 font-data text-micro text-ink0">{h.verb}</td>
                <td className="px-3 py-1.5 font-data text-micro text-ink1">{h.user}</td>
                <td className="max-w-[420px] truncate px-3 py-1.5 font-data text-micro text-ink2">
                  {h.sql}
                </td>
              </tr>
            ))}
            {detail.data?.history?.length === 0 && (
              <tr>
                <td colSpan={4} className="px-3 py-6 text-center text-body text-ink2">
                  Sin actividad reciente registrada.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  )
}
