import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Activity, KeyRound } from 'lucide-react'
import { useState } from 'react'

import { api } from '../lib/api'
import { useAuth } from '../lib/auth'

/** Mensaje de error llano; el backend ya manda 401/400 con detail cuando la actual no coincide. */
function friendly(err: unknown): string {
  const msg = (err as Error).message ?? ''
  if (msg.startsWith('401') || msg.startsWith('400')) return 'La contraseña actual no es correcta.'
  return msg || 'No se pudo cambiar la contraseña.'
}

/** Formulario de cambio de contraseña, reutilizable: cambio forzado (login) y voluntario (Ajustes). */
export function ChangePasswordForm({ onDone }: { onDone?: () => void }) {
  const qc = useQueryClient()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [okMsg, setOkMsg] = useState<string | null>(null)

  const m = useMutation({
    mutationFn: () => api.changePassword(current, next),
    onSuccess: () => {
      setCurrent('')
      setNext('')
      setConfirm('')
      setOkMsg('Contraseña actualizada.')
      qc.invalidateQueries({ queryKey: ['auth'] })
      onDone?.()
    },
  })

  const mismatch = confirm.length > 0 && next !== confirm
  const canSubmit = current && next && confirm && !mismatch

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        setOkMsg(null)
        if (canSubmit) m.mutate()
      }}
      className="space-y-4"
    >
      <label className="block">
        <span className="th">Contraseña actual</span>
        <input
          type="password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          autoFocus
          className="tap44 mt-1 w-full max-w-sm rounded border border-line bg-bg1 px-3 py-2 font-data text-body text-ink0"
        />
      </label>
      <label className="block">
        <span className="th">Contraseña nueva</span>
        <input
          type="password"
          value={next}
          onChange={(e) => setNext(e.target.value)}
          className="tap44 mt-1 w-full max-w-sm rounded border border-line bg-bg1 px-3 py-2 font-data text-body text-ink0"
        />
      </label>
      <label className="block">
        <span className="th">Repite la contraseña nueva</span>
        <input
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          className="tap44 mt-1 w-full max-w-sm rounded border border-line bg-bg1 px-3 py-2 font-data text-body text-ink0"
        />
        {mismatch && <span className="mt-1 block font-data text-micro text-crit">Las contraseñas no coinciden.</span>}
      </label>
      {m.isError && <p className="font-data text-micro text-crit">{friendly(m.error)}</p>}
      {okMsg && !m.isPending && <p className="font-data text-micro text-ok">{okMsg}</p>}
      <button
        type="submit"
        disabled={m.isPending || !canSubmit}
        className="tap44 rounded border border-line bg-bg2 px-4 py-2 font-dense text-label uppercase tracking-wide text-ink0 hover:bg-line disabled:opacity-50"
      >
        {m.isPending ? 'Guardando…' : 'Cambiar contraseña'}
      </button>
    </form>
  )
}

/** Pantalla forzada: no se puede saltar ni navegar hasta cambiar la contraseña (AuthGate). */
export function ChangePassword() {
  const { user, logout } = useAuth()

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg0 px-4">
      <div className="panel w-full max-w-sm space-y-4 p-6">
        <div className="flex items-center gap-2">
          <Activity size={18} strokeWidth={2} className="text-live" />
          <span className="font-dense text-lg font-semibold text-ink0">nz-monitor</span>
        </div>
        <div className="flex items-center gap-2 text-ink1">
          <KeyRound size={16} strokeWidth={1.5} />
          <p className="text-body">
            {user ? <span className="text-ink0">{user}</span> : 'Tu cuenta'}: por seguridad debes cambiar
            tu contraseña antes de continuar.
          </p>
        </div>
        <ChangePasswordForm />
        <button
          onClick={logout}
          className="tap44 w-full rounded border border-line px-3 py-1.5 font-dense text-label uppercase tracking-wide text-ink1 hover:bg-bg2 hover:text-ink0"
        >
          Salir
        </button>
      </div>
    </div>
  )
}
