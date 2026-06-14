import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { useState } from 'react'

import { api } from '../lib/api'

export function CodeSearch() {
  const dbsQ = useQuery({ queryKey: ['databases'], queryFn: api.databases })
  const [text, setText] = useState('')
  const [db, setDb] = useState('*')
  const [params, setParams] = useState<{ q: string; db: string } | null>(null)

  const q = useQuery({
    queryKey: ['search-code', params],
    queryFn: () => api.searchCode(params!.q, params!.db === '*' ? '' : params!.db),
    enabled: params !== null,
  })
  const rows = q.data?.rows ?? []

  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-dense text-lg font-semibold text-ink0">Buscar en código (SPs)</h1>
        <p className="text-body text-ink1">
          Encuentra tablas, campos o texto en el código de los stored procedures.
        </p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (text.trim().length >= 2) setParams({ q: text.trim(), db })
        }}
        className="panel flex flex-wrap items-end gap-3 p-4"
      >
        <label className="flex flex-1 flex-col gap-1">
          <span className="th">Texto a buscar</span>
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="INSUMOSMODELOSDR  ·  INSERT INTO X  ·  un campo…"
            className="w-full rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0 placeholder:text-ink2"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="th">Base</span>
          <select
            value={db}
            onChange={(e) => setDb(e.target.value)}
            className="rounded border border-line bg-bg1 px-2 py-1.5 font-data text-body text-ink0"
          >
            <option value="*">Todas (más lento)</option>
            {dbsQ.data?.databases.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          disabled={q.isFetching || text.trim().length < 2}
          className="inline-flex items-center gap-1.5 rounded border border-line bg-bg2 px-3 py-1.5 font-dense text-label uppercase tracking-wide text-ink0 hover:bg-line disabled:opacity-50"
        >
          <Search size={14} strokeWidth={1.6} /> Buscar
        </button>
      </form>

      {q.isError ? (
        <div className="panel px-4 py-8 text-center text-body text-crit">
          {(q.error as Error).message}
          <div className="mt-1 font-data text-micro text-ink2">¿VPN activa?</div>
        </div>
      ) : params ? (
        <section className="panel overflow-x-auto">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <h2 className="th">
              {q.isLoading ? 'buscando…' : `${rows.length} coincidencias`}
              {q.data?.truncated ? ' (tope alcanzado)' : ''}
            </h2>
          </div>
          <table className="w-full min-w-[680px]">
            <thead>
              <tr className="border-b border-line-strong">
                <th className="th px-3 py-2">Base</th>
                <th className="th px-3 py-2">Procedure</th>
                <th className="th px-3 py-2 text-right">Línea</th>
                <th className="th px-3 py-2">Código</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} className="border-b border-line last:border-0 hover:bg-bg2">
                  <td className="px-3 py-1.5 font-data text-micro text-ink1">{r.db}</td>
                  <td className="px-3 py-1.5 font-data text-body text-ink0">{r.procedure}</td>
                  <td className="num px-3 py-1.5 text-micro text-ink2">{r.line}</td>
                  <td className="max-w-[520px] truncate px-3 py-1.5 font-data text-micro text-ink1">
                    {r.snippet}
                  </td>
                </tr>
              ))}
              {!q.isLoading && rows.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-3 py-8 text-center text-body text-ink2">
                    Sin coincidencias.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      ) : (
        <div className="panel px-4 py-10 text-center text-body text-ink2">
          Escribe un texto y pulsa Buscar.
        </div>
      )}
    </div>
  )
}
