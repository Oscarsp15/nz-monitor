import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { useEffect, useState } from 'react'

import { ExportButton } from '../components/SearchInput'
import { KpiCard } from '../components/KpiCard'
import { exportToExcel, stamp } from '../lib/exportXlsx'
import { api } from '../lib/api'

interface OldFile {
  permissions: string
  size: string
  modified: string
  path: string
}

export function SftpOldFiles() {
  const cfg = useQuery({ queryKey: ['settings', 'sftp'], queryFn: api.getSftp })
  const [path, setPath] = useState('/')
  const [days, setDays] = useState(90)
  const [pattern, setPattern] = useState('*')
  const [params, setParams] = useState<{ path: string; days: number; pattern: string } | null>(null)

  useEffect(() => {
    if (cfg.data?.default_path) setPath((p) => (p === '/' ? cfg.data.default_path : p))
  }, [cfg.data])

  const q = useQuery({
    queryKey: ['sftp', 'old', params],
    queryFn: () => api.sftpOldFiles({ ...params!, max: 300 }),
    enabled: params !== null,
  })

  const rows = q.data?.rows ?? []
  const doExport = () =>
    exportToExcel<OldFile>(`archivos_viejos_${stamp()}.xlsx`, rows, [
      { header: 'Ruta', value: (r) => r.path },
      { header: 'Tamaño', value: (r) => r.size },
      { header: 'Modificado', value: (r) => r.modified },
      { header: 'Permisos', value: (r) => r.permissions },
    ])

  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-dense text-lg font-semibold text-ink0">Archivos viejos (SFTP)</h1>
        <p className="text-body text-ink1">Encuentra archivos antiguos para liberar espacio.</p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          setParams({ path, days, pattern })
        }}
        className="panel flex flex-wrap items-end gap-3 p-4"
      >
        <label className="flex flex-col gap-1">
          <span className="th">Ruta</span>
          <input
            value={path}
            onChange={(e) => setPath(e.target.value)}
            className="w-56 rounded border border-line bg-bg1 px-2 py-1 font-data text-body text-ink0"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="th">Antigüedad (días)</span>
          <input
            type="number"
            min={0}
            value={days}
            onChange={(e) => setDays(Math.max(0, Number(e.target.value) || 0))}
            className="w-28 rounded border border-line bg-bg1 px-2 py-1 font-data text-body text-ink0"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="th">Patrón</span>
          <input
            value={pattern}
            onChange={(e) => setPattern(e.target.value)}
            placeholder="*.csv"
            className="w-32 rounded border border-line bg-bg1 px-2 py-1 font-data text-body text-ink0 placeholder:text-ink2"
          />
        </label>
        <button
          type="submit"
          disabled={q.isFetching}
          className="inline-flex items-center gap-1.5 rounded border border-line bg-bg2 px-3 py-1.5 font-dense text-label uppercase tracking-wide text-ink0 hover:bg-line disabled:opacity-50"
        >
          <Search size={14} strokeWidth={1.6} /> Buscar
        </button>
      </form>

      {params && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          <KpiCard label="Encontrados" value={String(rows.length)} loading={q.isLoading} />
          <KpiCard label="Antigüedad" value={`> ${params.days} días`} />
          <KpiCard label="Patrón" value={params.pattern} />
        </div>
      )}

      {q.isError ? (
        <div className="panel px-4 py-8 text-center text-body text-crit">
          {(q.error as Error).message}
          <div className="mt-1 font-data text-micro text-ink2">¿VPN activa? ¿SFTP configurado?</div>
        </div>
      ) : params ? (
        <section className="panel overflow-x-auto">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <h2 className="th">Resultados</h2>
            <ExportButton onClick={doExport} disabled={rows.length === 0} />
          </div>
          <table className="w-full min-w-[640px]">
            <thead>
              <tr className="border-b border-line-strong">
                <th className="th px-3 py-2">Ruta</th>
                <th className="th px-3 py-2 text-right">Tamaño</th>
                <th className="th px-3 py-2">Modificado</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} className="border-b border-line last:border-0 hover:bg-bg2">
                  <td className="px-3 py-1.5 font-data text-micro text-ink0">{r.path}</td>
                  <td className="num px-3 py-1.5 text-body text-ink1">{r.size}</td>
                  <td className="px-3 py-1.5 font-data text-micro text-ink1">{r.modified}</td>
                </tr>
              ))}
              {!q.isLoading && rows.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-3 py-8 text-center text-body text-ink2">
                    Sin archivos que cumplan el criterio.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      ) : (
        <div className="panel px-4 py-10 text-center text-body text-ink2">
          Define ruta, antigüedad y patrón, y pulsa Buscar.
        </div>
      )}
    </div>
  )
}
