import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { PageSkeleton } from '../components/PageSkeleton'
import { StatusPill } from '../components/StatusPill'
import { api, clearToken } from '../lib/api'

export function Settings() {
  const qc = useQueryClient()

  const sftp = useQuery({ queryKey: ['settings', 'sftp'], queryFn: api.getSftp })
  const auth = useQuery({ queryKey: ['settings', 'auth'], queryFn: api.getAuth })
  const [auser, setAuser] = useState('')
  const [apass, setApass] = useState('')
  const saveAuth = useMutation({
    mutationFn: () => api.saveAuth({ username: auser, password: apass }),
    onSuccess: () => {
      setApass('')
      qc.invalidateQueries({ queryKey: ['settings', 'auth'] })
    },
  })
  const disableAuth = useMutation({
    mutationFn: () => api.saveAuth({ disable: true }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['settings', 'auth'] }),
  })

  const [sHost, setSHost] = useState('')
  const [sPort, setSPort] = useState(22)
  const [sUser, setSUser] = useState('')
  const [sPass, setSPass] = useState('')
  const [sDef, setSDef] = useState('/')
  const [sMsg, setSMsg] = useState<string | null>(null)

  useEffect(() => {
    if (sftp.data) {
      setSHost(sftp.data.host)
      setSPort(sftp.data.port)
      setSUser(sftp.data.user)
      setSDef(sftp.data.default_path || '/')
    }
  }, [sftp.data])

  const saveSftp = useMutation({
    mutationFn: () =>
      api.saveSftp({
        host: sHost,
        port: sPort,
        user: sUser,
        password: sPass || undefined,
        default_path: sDef,
      }),
    onSuccess: () => {
      setSPass('')
      qc.invalidateQueries({ queryKey: ['settings', 'sftp'] })
    },
  })
  const testSftp = useMutation({
    mutationFn: api.testSftp,
    onMutate: () => setSMsg(null),
    onSuccess: (r) =>
      setSMsg(r.status === 'connected' ? '✅ Conectado al SFTP.' : `❌ ${r.error || 'no conecta'}`),
    onError: (e) => setSMsg(`❌ ${(e as Error).message}`),
  })

  const loading = sftp.isLoading || auth.isLoading

  if (loading) {
    return (
      <div className="space-y-4">
        <h1 className="font-dense text-lg font-semibold text-ink0">Ajustes</h1>
        <PageSkeleton kpis={0} panels={1} />
      </div>
    )
  }

  return (
    <div className="reveal max-w-2xl space-y-5">
      <div>
        <h1 className="font-dense text-lg font-semibold text-ink0">Ajustes</h1>
        <p className="text-body text-ink1">Toda la configuración vive aquí (se guarda cifrada).</p>
      </div>

      <section className="panel overflow-hidden">
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <h2 className="th">Conexión SFTP</h2>
          <StatusPill status={sftp.data?.configured ? 'ok' : 'empty'} />
        </div>
        <div className="space-y-4 p-4">
          <p className="text-body text-ink1">
            Servidor SSH/SFTP para el monitor de disco y archivos viejos.
          </p>
          <div className="flex flex-wrap gap-3">
            <label className="flex flex-col gap-1">
              <span className="th">Host</span>
              <input
                value={sHost}
                onChange={(e) => setSHost(e.target.value)}
                placeholder="10.0.0.1"
                className="w-48 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0 placeholder:text-ink2"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="th">Puerto</span>
              <input
                type="number"
                value={sPort}
                onChange={(e) => setSPort(Number(e.target.value) || 22)}
                className="w-24 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="th">Usuario</span>
              <input
                value={sUser}
                onChange={(e) => setSUser(e.target.value)}
                className="w-40 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="th">Contraseña</span>
              <input
                type="password"
                value={sPass}
                onChange={(e) => setSPass(e.target.value)}
                placeholder={sftp.data?.has_password ? '•••••••• (guardada)' : '••••••••'}
                className="w-48 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0 placeholder:text-ink2"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="th">Ruta por defecto</span>
              <input
                value={sDef}
                onChange={(e) => setSDef(e.target.value)}
                placeholder="/nzscratch/nz"
                className="w-56 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0 placeholder:text-ink2"
              />
            </label>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => saveSftp.mutate()}
              disabled={saveSftp.isPending}
              className="rounded border border-line bg-bg2 px-3 py-1.5 font-dense text-label uppercase tracking-wide text-ink0 hover:bg-line disabled:opacity-50"
            >
              {saveSftp.isPending ? 'Guardando…' : 'Guardar'}
            </button>
            <button
              onClick={() => testSftp.mutate()}
              disabled={testSftp.isPending || !sftp.data?.configured}
              className="rounded border border-line px-3 py-1.5 font-dense text-label uppercase tracking-wide text-ink1 hover:bg-bg2 hover:text-ink0 disabled:opacity-50"
            >
              Probar conexión
            </button>
            {sMsg && <span className="font-data text-micro text-ink1">{sMsg}</span>}
          </div>
        </div>
      </section>

      <section className="panel overflow-hidden">
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <h2 className="th">Seguridad · Login</h2>
          <StatusPill status={auth.data?.configured ? 'ok' : 'empty'} />
        </div>
        <div className="space-y-4 p-4">
          <p className="text-body text-ink1">
            <b>Opcional.</b> Si activas login, la app pedirá usuario y contraseña. Sin esto, queda
            abierta en tu red local.
          </p>
          {auth.data?.configured ? (
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-body text-ink1">
                Login activo · usuario <span className="font-data text-ink0">{auth.data.user}</span>
              </span>
              <button
                onClick={() => {
                  clearToken()
                  location.reload()
                }}
                className="rounded border border-line px-3 py-1.5 font-dense text-label uppercase tracking-wide text-ink1 hover:bg-bg2 hover:text-ink0"
              >
                Cerrar sesión
              </button>
              <button
                onClick={() => disableAuth.mutate()}
                disabled={disableAuth.isPending}
                className="rounded border border-line px-3 py-1.5 font-dense text-label uppercase tracking-wide text-crit hover:bg-bg2 disabled:opacity-50"
              >
                Desactivar login
              </button>
            </div>
          ) : (
            <div className="flex flex-wrap items-end gap-3">
              <label className="flex flex-col gap-1">
                <span className="th">Usuario</span>
                <input
                  value={auser}
                  onChange={(e) => setAuser(e.target.value)}
                  className="w-40 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="th">Contraseña</span>
                <input
                  type="password"
                  value={apass}
                  onChange={(e) => setApass(e.target.value)}
                  className="w-48 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0"
                />
              </label>
              <button
                onClick={() => saveAuth.mutate()}
                disabled={saveAuth.isPending || !auser || !apass}
                className="rounded border border-line bg-bg2 px-3 py-1.5 font-dense text-label uppercase tracking-wide text-ink0 hover:bg-line disabled:opacity-50"
              >
                Activar login
              </button>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
