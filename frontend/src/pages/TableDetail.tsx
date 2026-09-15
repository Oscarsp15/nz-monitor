import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Lock } from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import { KpiCard } from '../components/KpiCard'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { dt, fixed, gb } from '../lib/format'

export function TableDetail() {
  const { objid } = useParams()
  const id = Number(objid)
  const [sp] = useSearchParams()
  const name = sp.get('name') ?? ''
  const { isOperador } = useAuth()

  // El detalle de tabla es en vivo (/api/table, /api/table/slices — la de historial es la
  // consulta más cara de toda la app) y el backend la exige operador+. Para `viewer` ni se
  // dispara: si llega por URL directa (p. ej. un enlace guardado), se le explica por qué en vez
  // de dejarle ver un 403 crudo o una pantalla vacía.
  const detail = useQuery({
    queryKey: ['table', id],
    queryFn: () => api.tableDetail(id, name),
    enabled: Number.isFinite(id) && isOperador,
  })
  const slices = useQuery({
    queryKey: ['slices', id],
    queryFn: () => api.tableSlices(id),
    enabled: Number.isFinite(id) && isOperador,
  })

  // Carga ATÓMICA (AGENTS §12): no pintar nada hasta que ambas consultas terminen.
  const loading = isOperador && (detail.isLoading || slices.isLoading)
  const forbidden =
    !isOperador ||
    (detail.error as Error | undefined)?.message === 'No tienes permisos para esta acción' ||
    (slices.error as Error | undefined)?.message === 'No tienes permisos para esta acción'
  const error = (detail.isError || slices.isError) && !forbidden
  const meta = detail.data?.meta
  const sliceRows = slices.data?.slices ?? []
  const occupied = slices.data?.occupied ?? sliceRows.length
  const maxGb = Math.max(0, ...sliceRows.map((s) => s.gb))

  return (
    <div className="space-y-5">
      <Link
        to="/tablas"
        className="tap44 -ml-2 inline-flex items-center gap-1 rounded px-2 font-dense text-label uppercase tracking-wide text-ink1 hover:text-ink0"
      >
        <ArrowLeft size={14} /> Volver
      </Link>

      <div>
        <h1 className="break-all font-data text-lg text-ink0">{name || `objid ${id}`}</h1>
        {meta && (
          <p className="font-data text-micro text-ink2">
            {meta.db}.{meta.sch} · owner {meta.owner} · creada {dt(meta.created)}
          </p>
        )}
      </div>

      {loading ? (
        // Esqueleto atenuado mientras carga TODO (evita la aparición escalonada)
        <div className="space-y-5">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="panel h-[72px] animate-pulse opacity-40" />
            ))}
          </div>
          <div className="panel h-32 animate-pulse opacity-40" />
          <div className="panel h-40 animate-pulse opacity-40" />
        </div>
      ) : forbidden ? (
        <div className="panel flex flex-col items-center gap-3 px-4 py-10 text-center">
          <Lock size={20} strokeWidth={1.5} className="text-ink2" />
          <p className="text-body text-ink0">Tu rol no permite consultas en vivo.</p>
          <p className="max-w-sm font-data text-micro text-ink2">
            Ver el detalle de una tabla consulta el appliance al instante. Pide a un operador o
            administrador que lo revise, o vuelve a la lista de tablas.
          </p>
          <Link
            to="/tablas"
            className="tap44 mt-1 inline-flex items-center gap-1 rounded border border-line px-3 font-dense text-label uppercase tracking-wide text-ink1 hover:bg-bg2 hover:text-ink0"
          >
            <ArrowLeft size={14} /> Volver a tablas
          </Link>
        </div>
      ) : error ? (
        <div className="panel px-4 py-8 text-center text-body text-crit">
          No se pudo cargar el detalle.
          <div className="mt-1 font-data text-micro text-ink2">¿VPN activa?</div>
        </div>
      ) : (
        // Todo junto, con un fade sutil
        <div className="reveal space-y-5">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <KpiCard label="Espacio" value={gb(meta?.gb)} />
            <KpiCard label="Skew" value={fixed(meta?.skew)} sub="0 = parejo · alto = desigual" />
            <KpiCard label="Dataslices ocupados" value={String(occupied)} sub="de 192 (≠ skew)" />
          </div>

          <div className="grid gap-5 xl:grid-cols-2 xl:items-start">
          <section className="panel overflow-hidden">
            <div className="border-b border-line px-4 py-2.5">
              <h2 className="th">
                Dataslices más cargados
                {occupied > sliceRows.length ? ` · top ${sliceRows.length} de ${occupied}` : ''}
              </h2>
            </div>
            <div className="space-y-1 p-3">
              {sliceRows.map((s) => (
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
              {sliceRows.length === 0 && (
                <p className="px-1 py-4 text-center text-body text-ink2">Sin datos de dataslices.</p>
              )}
            </div>
          </section>

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
                    <td className="px-3 py-1.5 font-data text-micro text-ink1">{dt(h.tend)}</td>
                    <td className="px-3 py-1.5 font-data text-micro text-ink0">{h.verb}</td>
                    <td className="px-3 py-1.5 font-data text-micro text-ink1">{h.user}</td>
                    <td className="max-w-[420px] truncate px-3 py-1.5 font-data text-micro text-ink2">
                      {h.sql}
                    </td>
                  </tr>
                ))}
                {(detail.data?.history?.length ?? 0) === 0 && (
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
        </div>
      )}
    </div>
  )
}
