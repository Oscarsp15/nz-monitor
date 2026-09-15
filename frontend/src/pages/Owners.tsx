import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { ExportButton, SearchInput } from '../components/SearchInput'
import { FreshnessSeal } from '../components/FreshnessSeal'
import { KpiCard } from '../components/KpiCard'
import { PageSkeleton } from '../components/PageSkeleton'
import { RefreshButton } from '../components/RefreshButton'
import { api, type OwnerRow } from '../lib/api'
import { exportToExcel, stamp } from '../lib/exportXlsx'
import { ageFromAt, gb, int } from '../lib/format'

export function Owners() {
  const [sp, setSp] = useSearchParams()
  const db = sp.get('db') || '*'
  const dbsQ = useQuery({ queryKey: ['databases'], queryFn: api.databases })
  const [filter, setFilter] = useState('')
  const freshRef = useRef(false)

  const q = useQuery({
    queryKey: ['owners', db],
    queryFn: async () => {
      const fresh = freshRef.current
      freshRef.current = false
      return api.owners(db, fresh)
    },
    placeholderData: keepPreviousData,
  })
  const refreshNow = () => {
    freshRef.current = true
    q.refetch()
  }

  // Carga ATÓMICA + revalidación visible (§2.1/§8/§12): esqueleto sin dato previo; con dato
  // previo, atenuado y marcado "actualizando…" mientras cualquier consulta dependiente está
  // en vuelo — nunca se muestra el valor viejo de otra base sin avisar.
  const loading = q.isLoading || dbsQ.isLoading
  const updating = q.isFetching || dbsQ.isFetching
  const all = q.data?.rows ?? []
  const rows = filter
    ? all.filter((r) => r.owner?.toUpperCase().includes(filter.toUpperCase()))
    : all
  const totalGb = rows.reduce((a, r) => a + r.gb, 0)
  const totalTables = rows.reduce((a, r) => a + r.tablas, 0)

  const doExport = () => {
    exportToExcel<OwnerRow>(
      `owners_${db === '*' ? 'todas' : db}_${stamp()}.xlsx`,
      rows,
      [
        { header: 'Owner', value: (r) => r.owner },
        { header: 'Tablas', value: (r) => r.tablas },
        { header: 'Espacio GB', value: (r) => r.gb },
      ],
      'Owners',
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-dense text-lg font-semibold text-ink0">Espacio por owner</h1>
          <p className="text-body text-ink1">Quién ocupa el espacio — útil para depurar.</p>
        </div>
        <div className="flex items-center gap-2">
          <FreshnessSeal ageSeconds={ageFromAt(q.data?.at)} updating={updating} />
          <div className="hidden lg:block">
            <RefreshButton onClick={refreshNow} busy={updating} />
          </div>
        </div>
      </div>

      {loading ? (
        <PageSkeleton kpis={3} />
      ) : (
      <div className={`reveal space-y-4 transition-opacity duration-200 ${updating ? 'opacity-50' : ''}`}>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <KpiCard label="Owners" value={int(rows.length)} />
        <KpiCard label="Tablas" value={int(totalTables)} />
        <KpiCard label="Espacio total" value={gb(totalGb)} />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 font-dense text-label uppercase tracking-wide text-ink1">
          Base
          <select
            value={db}
            onChange={(e) => setSp(e.target.value === '*' ? {} : { db: e.target.value })}
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
        <SearchInput value={filter} onChange={setFilter} placeholder="Owner…" />
        <ExportButton onClick={doExport} disabled={rows.length === 0} />
      </div>

      {/* Fichas (<640px, DESIGN §9.3): nombre a ancho completo + las cifras que importan. */}
      <div className="space-y-2 sm:hidden">
        {q.isError && (
          <div className="panel px-4 py-8 text-center text-body text-crit">
            {(q.error as Error).message}
            <div className="mt-1 font-data text-micro text-ink2">¿VPN activa?</div>
          </div>
        )}
        {rows.map((r) => (
          <div key={r.owner} className="tap44-row panel px-4 py-3">
            <div className="break-all font-data text-body text-ink0">{r.owner}</div>
            <div className="mt-2 flex items-center justify-between gap-3">
              <div>
                <div className="th">Tablas</div>
                <div className="num text-body text-ink0">{int(r.tablas)}</div>
              </div>
              <div className="text-right">
                <div className="th">Espacio</div>
                <div className="num text-body text-ink0">{gb(r.gb)}</div>
              </div>
            </div>
            <span className="mt-2 block h-1.5 w-full rounded-pill bg-line-strong">
              <span
                className="block h-full rounded-pill bg-info"
                style={{ width: `${totalGb ? (r.gb / totalGb) * 100 : 0}%` }}
              />
            </span>
          </div>
        ))}
        {!q.isError && !q.isLoading && rows.length === 0 && (
          <div className="panel px-4 py-8 text-center text-body text-ink2">Sin datos.</div>
        )}
      </div>

      <section className="panel hidden overflow-x-auto sm:block">
        <table className="w-full min-w-[480px]">
          <thead>
            <tr className="border-b border-line-strong">
              <th className="th px-3 py-2">Owner</th>
              <th className="th px-3 py-2 text-right">Tablas</th>
              <th className="th px-3 py-2 text-right">Espacio</th>
              <th className="th px-3 py-2">Proporción</th>
            </tr>
          </thead>
          <tbody>
            {q.isError && (
              <tr>
                <td colSpan={4} className="px-3 py-8 text-center text-body text-crit">
                  {(q.error as Error).message}
                  <div className="mt-1 font-data text-micro text-ink2">¿VPN activa?</div>
                </td>
              </tr>
            )}
            {rows.map((r) => (
              <tr key={r.owner} className="border-b border-line last:border-0 hover:bg-bg2">
                <td className="px-3 py-1.5 font-data text-body text-ink0">{r.owner}</td>
                <td className="num px-3 py-1.5 text-body text-ink1">{int(r.tablas)}</td>
                <td className="num px-3 py-1.5 text-body text-ink0">{gb(r.gb)}</td>
                <td className="px-3 py-1.5">
                  <span className="block h-1.5 w-full rounded-pill bg-line-strong">
                    <span
                      className="block h-full rounded-pill bg-info"
                      style={{ width: `${totalGb ? (r.gb / totalGb) * 100 : 0}%` }}
                    />
                  </span>
                </td>
              </tr>
            ))}
            {!q.isError && !q.isLoading && rows.length === 0 && (
              <tr>
                <td colSpan={4} className="px-3 py-8 text-center text-body text-ink2">
                  Sin datos.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <div className="flex justify-center border-t border-line pt-4 lg:hidden">
        <RefreshButton onClick={refreshNow} busy={updating} />
      </div>
      </div>
      )}
    </div>
  )
}
