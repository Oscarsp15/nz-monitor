import { useQuery } from '@tanstack/react-query'
import { useRef, useState } from 'react'

import { KpiCard } from '../components/KpiCard'
import { PageSkeleton } from '../components/PageSkeleton'
import { RefreshButton } from '../components/RefreshButton'
import { SearchInput } from '../components/SearchInput'
import { api } from '../lib/api'

function pct(s?: string): number {
  return s ? Number(s.replace('%', '')) || 0 : 0
}

export function SftpDisk() {
  const [path, setPath] = useState('/')
  const [duPath, setDuPath] = useState('/')
  const freshRef = useRef(false)

  const disk = useQuery({ queryKey: ['sftp', 'disk', path], queryFn: () => api.sftpDisk(path) })
  const du = useQuery({ queryKey: ['sftp', 'du', duPath], queryFn: () => api.sftpDu(duPath, 20) })

  const loading = disk.isLoading || du.isLoading
  const use = pct(disk.data?.use_percent)
  const color = use >= 90 ? 'var(--crit)' : use >= 80 ? 'var(--warn)' : 'var(--ok)'

  const refreshNow = () => {
    freshRef.current = true
    disk.refetch()
    du.refetch()
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-dense text-lg font-semibold text-ink0">Espacio en disco (SFTP)</h1>
          <p className="text-body text-ink1">Uso del filesystem y carpetas más pesadas.</p>
        </div>
        <RefreshButton onClick={refreshNow} busy={disk.isFetching || du.isFetching} />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 font-dense text-label uppercase tracking-wide text-ink1">
          Ruta
          <SearchInput value={path} onChange={setPath} placeholder="/" />
        </label>
      </div>

      {disk.isError ? (
        <div className="panel px-4 py-8 text-center text-body text-crit">
          {(disk.error as Error).message}
          <div className="mt-1 font-data text-micro text-ink2">¿VPN activa? ¿SFTP configurado en Ajustes?</div>
        </div>
      ) : loading ? (
        <PageSkeleton kpis={3} panels={1} />
      ) : (
        <div className="reveal space-y-4">
          {disk.data?.error ? (
            <div className="panel px-4 py-6 text-center text-body text-warn">{disk.data.error}</div>
          ) : (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <KpiCard label="Tamaño" value={disk.data?.size ?? '—'} />
              <KpiCard label="Usado" value={disk.data?.used ?? '—'} />
              <KpiCard label="Disponible" value={disk.data?.available ?? '—'} />
              <div className="panel px-4 py-3">
                <div className="th">% uso</div>
                <div className="mt-1 font-data kpi-value" style={{ color }}>
                  {disk.data?.use_percent ?? '—'}
                </div>
                <div className="mt-1 font-data text-micro text-ink2">{disk.data?.mounted_on}</div>
              </div>
            </div>
          )}

          <section className="panel overflow-hidden">
            <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
              <h2 className="th">Carpetas más pesadas</h2>
              <SearchInput value={duPath} onChange={setDuPath} placeholder="/ruta" />
            </div>
            <div className="divide-y divide-line">
              {(du.data?.rows ?? []).map((r) => (
                <div key={r.path} className="flex items-center justify-between px-4 py-1.5">
                  <span className="truncate font-data text-body text-ink0">{r.path}</span>
                  <span className="num ml-3 shrink-0 text-body text-ink1">{r.size}</span>
                </div>
              ))}
              {(du.data?.rows ?? []).length === 0 && (
                <div className="px-4 py-6 text-center text-body text-ink2">
                  Sin datos (ruta vacía o sin permisos).
                </div>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
