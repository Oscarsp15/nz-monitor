import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { KeyRound, Plus, Power, Trash2, X } from 'lucide-react'
import { useState } from 'react'

import { KpiCard } from '../components/KpiCard'
import { PageSkeleton } from '../components/PageSkeleton'
import { api, type AppUser, type Role } from '../lib/api'
import { useAuth } from '../lib/auth'
import { dt, int } from '../lib/format'

const ROLE_LABEL: Record<Role, string> = { admin: 'Administrador', operador: 'Operador', viewer: 'Visor' }
const ROLES: Role[] = ['admin', 'operador', 'viewer']

function ActivePill({ active }: { active: boolean }) {
  const c = active ? 'var(--ok)' : 'var(--crit)'
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-pill px-2 py-0.5 font-data text-micro"
      style={{ color: c, background: `color-mix(in srgb, ${c} 12%, transparent)` }}
    >
      <span className="h-1.5 w-1.5 rounded-pill" style={{ background: c }} aria-hidden />
      {active ? 'Activo' : 'Inactivo'}
    </span>
  )
}

export function Users() {
  const qc = useQueryClient()
  const { user: currentUser } = useAuth()

  const q = useQuery({ queryKey: ['users'], queryFn: api.users })

  const [errMsg, setErrMsg] = useState<string | null>(null)
  const [pendingId, setPendingId] = useState<number | null>(null)

  const [showCreate, setShowCreate] = useState(false)
  const [cUser, setCUser] = useState('')
  const [cPass, setCPass] = useState('')
  const [cRole, setCRole] = useState<Role>('viewer')

  const createUser = useMutation({
    mutationFn: () => api.createUser({ username: cUser, password: cPass, role: cRole }),
    onMutate: () => setErrMsg(null),
    onSuccess: () => {
      setCUser('')
      setCPass('')
      setCRole('viewer')
      setShowCreate(false)
      qc.invalidateQueries({ queryKey: ['users'] })
    },
    onError: (e) => setErrMsg((e as Error).message),
  })

  const patchUser = useMutation({
    mutationFn: ({ id, body }: { id: number; body: { role?: Role; active?: boolean; password?: string } }) =>
      api.updateUser(id, body),
    onMutate: ({ id }) => {
      setPendingId(id)
      setErrMsg(null)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
    onError: (e) => setErrMsg((e as Error).message),
    onSettled: () => setPendingId(null),
  })

  const removeUser = useMutation({
    mutationFn: (id: number) => api.deleteUser(id),
    onMutate: (id) => {
      setPendingId(id)
      setErrMsg(null)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
    onError: (e) => setErrMsg((e as Error).message),
    onSettled: () => setPendingId(null),
  })

  const rows = q.data?.users ?? []
  const loading = q.isLoading
  const canCreate = cUser.trim() && cPass && !createUser.isPending

  const handleRoleChange = (u: AppUser, role: Role) => {
    if (role === u.role) return
    patchUser.mutate({ id: u.id, body: { role } })
  }

  const handleToggleActive = (u: AppUser) => {
    const next = !u.active
    if (!next && !window.confirm(`¿Desactivar a "${u.username}"? No podrá iniciar sesión.`)) return
    patchUser.mutate({ id: u.id, body: { active: next } })
  }

  const handleResetPassword = (u: AppUser) => {
    const pw = window.prompt(`Nueva contraseña para "${u.username}":`)
    if (!pw) return
    if (!window.confirm(`¿Confirmas restablecer la contraseña de "${u.username}"?`)) return
    patchUser.mutate({ id: u.id, body: { password: pw } })
  }

  const handleDelete = (u: AppUser) => {
    if (!window.confirm(`¿Eliminar al usuario "${u.username}"? Esta acción no se puede deshacer.`)) return
    removeUser.mutate(u.id)
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-dense text-lg font-semibold text-ink0">Usuarios</h1>
          <p className="text-body text-ink1">Quién puede entrar y qué puede hacer.</p>
        </div>
        <button
          onClick={() => {
            setShowCreate((v) => !v)
            setErrMsg(null)
          }}
          className="inline-flex items-center gap-1.5 rounded border border-line bg-bg2 px-3 py-1.5 font-dense text-label uppercase tracking-wide text-ink0 hover:bg-line"
        >
          {showCreate ? <X size={14} strokeWidth={1.5} /> : <Plus size={14} strokeWidth={1.5} />}
          {showCreate ? 'Cancelar' : 'Nuevo usuario'}
        </button>
      </div>

      {loading ? (
        <PageSkeleton kpis={3} panels={showCreate ? 2 : 1} />
      ) : (
        <div className="reveal space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <KpiCard label="Usuarios" value={int(rows.length)} />
            <KpiCard label="Activos" value={int(rows.filter((u) => u.active).length)} />
            <KpiCard label="Administradores" value={int(rows.filter((u) => u.role === 'admin').length)} />
          </div>

          {showCreate && (
            <section className="panel overflow-hidden">
              <div className="border-b border-line px-4 py-2.5">
                <h2 className="th">Nuevo usuario</h2>
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  if (canCreate) createUser.mutate()
                }}
                className="flex flex-wrap items-end gap-3 p-4"
              >
                <label className="flex flex-col gap-1">
                  <span className="th">Usuario</span>
                  <input
                    value={cUser}
                    onChange={(e) => setCUser(e.target.value)}
                    autoFocus
                    className="w-40 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="th">Contraseña temporal</span>
                  <input
                    type="password"
                    value={cPass}
                    onChange={(e) => setCPass(e.target.value)}
                    className="w-48 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="th">Rol</span>
                  <select
                    value={cRole}
                    onChange={(e) => setCRole(e.target.value as Role)}
                    className="rounded border border-line bg-bg1 px-2 py-1.5 font-data text-body text-ink0"
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {ROLE_LABEL[r]}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="submit"
                  disabled={!canCreate}
                  className="rounded border border-line bg-bg2 px-3 py-1.5 font-dense text-label uppercase tracking-wide text-ink0 hover:bg-line disabled:opacity-50"
                >
                  {createUser.isPending ? 'Creando…' : 'Crear'}
                </button>
                <p className="w-full font-data text-micro text-ink2">
                  Pedirá cambiar la contraseña en el primer inicio de sesión.
                </p>
              </form>
            </section>
          )}

          {errMsg && (
            <p
              className="rounded border px-3 py-2 font-data text-micro text-crit"
              style={{
                borderColor: 'color-mix(in srgb, var(--crit) 40%, transparent)',
                background: 'color-mix(in srgb, var(--crit) 8%, transparent)',
              }}
            >
              {errMsg}
            </p>
          )}

          <section className="panel overflow-x-auto">
            <table className="w-full min-w-[720px]">
              <thead>
                <tr className="border-b border-line-strong">
                  <th className="th px-3 py-2">Usuario</th>
                  <th className="th px-3 py-2">Rol</th>
                  <th className="th px-3 py-2">Estado</th>
                  <th className="th px-3 py-2">Creado</th>
                  <th className="th px-3 py-2">Último acceso</th>
                  <th className="th px-3 py-2 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {q.isError && (
                  <tr>
                    <td colSpan={6} className="px-3 py-8 text-center text-body text-crit">
                      {(q.error as Error).message}
                    </td>
                  </tr>
                )}
                {!q.isError &&
                  rows.map((u) => {
                    const isSelf = u.username === currentUser
                    const busy = patchUser.isPending || removeUser.isPending
                    const rowBusy = busy && pendingId === u.id
                    return (
                      <tr key={u.id} className="border-b border-line last:border-0 hover:bg-bg2">
                        <td className="px-3 py-1.5">
                          <div className="font-data text-body text-ink0">
                            {u.username}
                            {isSelf && <span className="ml-1.5 text-micro text-ink2">(tú)</span>}
                          </div>
                          {u.must_change_password && (
                            <div className="font-data text-micro text-warn">pendiente de cambiar contraseña</div>
                          )}
                        </td>
                        <td className="px-3 py-1.5">
                          <select
                            value={u.role}
                            disabled={rowBusy}
                            onChange={(e) => handleRoleChange(u, e.target.value as Role)}
                            className="rounded border border-line bg-bg1 px-2 py-1 font-data text-body text-ink0 disabled:opacity-50"
                          >
                            {ROLES.map((r) => (
                              <option key={r} value={r}>
                                {ROLE_LABEL[r]}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-3 py-1.5">
                          <ActivePill active={u.active} />
                        </td>
                        <td className="px-3 py-1.5 font-data text-micro text-ink1">{dt(u.created_at)}</td>
                        <td className="px-3 py-1.5 font-data text-micro text-ink1">{dt(u.last_login_at)}</td>
                        <td className="px-3 py-1.5">
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => handleResetPassword(u)}
                              disabled={rowBusy}
                              title="Resetear contraseña"
                              className="rounded border border-line p-1.5 text-ink1 hover:bg-bg2 hover:text-ink0 disabled:opacity-50"
                            >
                              <KeyRound size={14} strokeWidth={1.5} />
                            </button>
                            <button
                              onClick={() => handleToggleActive(u)}
                              disabled={rowBusy || isSelf}
                              title={
                                isSelf
                                  ? 'No puedes desactivar tu propia cuenta'
                                  : u.active
                                    ? 'Desactivar'
                                    : 'Activar'
                              }
                              className="rounded border border-line p-1.5 text-ink1 hover:bg-bg2 hover:text-ink0 disabled:opacity-50"
                            >
                              <Power size={14} strokeWidth={1.5} />
                            </button>
                            <button
                              onClick={() => handleDelete(u)}
                              disabled={rowBusy || isSelf}
                              title={isSelf ? 'No puedes eliminar tu propia cuenta' : 'Eliminar'}
                              className="rounded border border-line p-1.5 text-crit hover:bg-bg2 disabled:opacity-50"
                            >
                              <Trash2 size={14} strokeWidth={1.5} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                {!q.isError && rows.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-3 py-8 text-center text-body text-ink2">
                      Sin usuarios.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </section>
        </div>
      )}
    </div>
  )
}
