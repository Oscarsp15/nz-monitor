import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { PageSkeleton } from '../components/PageSkeleton'
import { StatusPill } from '../components/StatusPill'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { ChangePasswordForm } from './ChangePassword'

export function Settings() {
  const qc = useQueryClient()
  const { isAdmin } = useAuth()

  // /settings/sftp es solo-admin (contrato de permisos); no consultarlo para el resto de roles.
  const sftp = useQuery({ queryKey: ['settings', 'sftp'], queryFn: api.getSftp, enabled: isAdmin })

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

  // Carga atómica: mientras haya algo por resolver (solo aplica a admin, que consulta SFTP).
  const loading = isAdmin && sftp.isLoading

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
        <div className="border-b border-line px-4 py-2.5">
          <h2 className="th">Mi contraseña</h2>
        </div>
        <div className="p-4">
          <ChangePasswordForm />
        </div>
      </section>

      {isAdmin && (
        <section className="panel overflow-hidden">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <h2 className="th">Usuarios</h2>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 p-4">
            <p className="text-body text-ink1">Crear usuarios, cambiar roles, activar/desactivar o borrar.</p>
            <Link
              to="/usuarios"
              className="tap44 inline-flex items-center justify-center gap-1.5 rounded border border-line bg-bg2 px-3 py-1.5 font-dense text-label uppercase tracking-wide text-ink0 hover:bg-line"
            >
              <Users size={14} strokeWidth={1.5} />
              Administrar usuarios
            </Link>
          </div>
        </section>
      )}

      {isAdmin && (
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
                  className="tap44 w-48 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0 placeholder:text-ink2"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="th">Puerto</span>
                <input
                  type="number"
                  value={sPort}
                  onChange={(e) => setSPort(Number(e.target.value) || 22)}
                  className="tap44 w-24 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="th">Usuario</span>
                <input
                  value={sUser}
                  onChange={(e) => setSUser(e.target.value)}
                  className="tap44 w-40 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="th">Contraseña</span>
                <input
                  type="password"
                  value={sPass}
                  onChange={(e) => setSPass(e.target.value)}
                  placeholder={sftp.data?.has_password ? '•••••••• (guardada)' : '••••••••'}
                  className="tap44 w-48 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0 placeholder:text-ink2"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="th">Ruta por defecto</span>
                <input
                  value={sDef}
                  onChange={(e) => setSDef(e.target.value)}
                  placeholder="/nzscratch/nz"
                  className="tap44 w-56 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0 placeholder:text-ink2"
                />
              </label>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => saveSftp.mutate()}
                disabled={saveSftp.isPending}
                className="tap44 rounded border border-line bg-bg2 px-3 py-1.5 font-dense text-label uppercase tracking-wide text-ink0 hover:bg-line disabled:opacity-50"
              >
                {saveSftp.isPending ? 'Guardando…' : 'Guardar'}
              </button>
              <button
                onClick={() => testSftp.mutate()}
                disabled={testSftp.isPending || !sftp.data?.configured}
                className="tap44 rounded border border-line px-3 py-1.5 font-dense text-label uppercase tracking-wide text-ink1 hover:bg-bg2 hover:text-ink0 disabled:opacity-50"
              >
                Probar conexión
              </button>
              {sMsg && <span className="font-data text-micro text-ink1">{sMsg}</span>}
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
