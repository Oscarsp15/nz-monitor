import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { FreshnessSeal } from '../components/FreshnessSeal'
import { RefreshButton } from '../components/RefreshButton'
import { SkewBadge } from '../components/SkewBadge'
import { api } from '../lib/api'
import { ageFromAt, gb } from '../lib/format'
import { useLiveMode } from '../hooks/useLiveMode'

const COLS: { key: string; label: string; order?: string; num?: boolean }[] = [
  { key: 'table', label: 'Tabla' },
  { key: 'db', label: 'Base' },
  { key: 'owner', label: 'Owner' },
  { key: 'distribute_on', label: 'Distribución' },
  { key: 'space_gb', label: 'Espacio', order: 'space', num: true },
  { key: 'skew', label: 'Skew', order: 'skew', num: true },
]

export function Tables() {
  const navigate = useNavigate()
  const [sp, setSp] = useSearchParams()
  const dbsQ = useQuery({ queryKey: ['databases'], queryFn: api.databases })

  const db = sp.get('db') || '*'
  const [order, setOrder] = useState('space')
  const [page, setPage] = useState(0)
  const freshRef = useRef(false)

  const setDb = (value: string) => {
    setSp(value === '*' ? {} : { db: value })
    setPage(0)
  }

  const q = useQuery({
    queryKey: ['tables', db, order, page],
    queryFn: async () => {
      const fresh = freshRef.current
      freshRef.current = false
      return api.tables({ db, order, page, fresh })
    },
  })

  const refreshNow = () => {
    freshRef.current = true
    q.refetch()
  }
  const { live, setLive } = useLiveMode(refreshNow)

  const setOrderCol = (col?: string) => {
    if (!col) return
    setOrder(col)
    setPage(0)
  }

  const rows = q.data?.rows ?? []

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
          <FreshnessSeal ageSeconds={ageFromAt(q.data?.at)} live={live} />
          <RefreshButton onClick={refreshNow} busy={q.isFetching} />
        </div>
      </div>

      {/* Controles */}
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 font-dense text-label uppercase tracking-wide text-ink1">
          Base
          <select
            value={db}
            onChange={(e) => setDb(e.target.value)}
            className="rounded border border-line bg-bg1 px-2 py-1 font-data text-body text-ink0"
          >
            <option value="*">Todas</option>
            {dbsQ.data?.databases.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <label className="ml-auto flex cursor-pointer items-center gap-2 font-dense text-label uppercase tracking-wide text-ink1">
          <input
            type="checkbox"
            checked={live}
            onChange={(e) => setLive(e.target.checked)}
            className="accent-[var(--live)]"
          />
          Modo en vivo
        </label>
      </div>

      {/* Tabla */}
      <section className="panel overflow-x-auto">
        <table className="w-full min-w-[680px]">
          <thead>
            <tr className="border-b border-line-strong">
              {COLS.map((c) => (
                <th
                  key={c.key}
                  onClick={() => setOrderCol(c.order)}
                  className={`th px-3 py-2 ${c.num ? 'text-right' : ''} ${
                    c.order ? 'cursor-pointer select-none hover:text-ink0' : ''
                  } ${order === c.order ? 'text-ink0' : ''}`}
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
                  onClick={() =>
                    navigate(`/tabla/${r.objid}?name=${encodeURIComponent(r.table ?? '')}`)
                  }
                  className="cursor-pointer border-b border-line last:border-0 hover:bg-bg2"
                >
                  <td className="px-3 py-1.5 font-data text-body text-ink0">{r.table}</td>
                  <td className="px-3 py-1.5 font-data text-body text-ink1">{r.db}</td>
                  <td className="px-3 py-1.5 font-data text-body text-ink1">{r.owner}</td>
                  <td className="px-3 py-1.5 font-data text-micro text-ink1">{r.distribute_on}</td>
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
  )
}
