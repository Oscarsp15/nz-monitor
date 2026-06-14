import { useMutation } from '@tanstack/react-query'
import { Activity } from 'lucide-react'
import { useState } from 'react'

import { api, setToken } from '../lib/api'

export function Login() {
  const [user, setUser] = useState('')
  const [pass, setPass] = useState('')
  const m = useMutation({
    mutationFn: () => api.login(user, pass),
    onSuccess: (r) => {
      setToken(r.token)
      location.reload()
    },
  })

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg0 px-4">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (user && pass) m.mutate()
        }}
        className="panel w-full max-w-sm space-y-4 p-6"
      >
        <div className="flex items-center gap-2">
          <Activity size={18} strokeWidth={2} className="text-live" />
          <span className="font-dense text-lg font-semibold text-ink0">nz-monitor</span>
        </div>
        <p className="text-body text-ink1">Inicia sesión para continuar.</p>
        <label className="block">
          <span className="th">Usuario</span>
          <input
            value={user}
            onChange={(e) => setUser(e.target.value)}
            autoFocus
            className="mt-1 w-full rounded border border-line bg-bg1 px-3 py-2 font-data text-body text-ink0"
          />
        </label>
        <label className="block">
          <span className="th">Contraseña</span>
          <input
            type="password"
            value={pass}
            onChange={(e) => setPass(e.target.value)}
            className="mt-1 w-full rounded border border-line bg-bg1 px-3 py-2 font-data text-body text-ink0"
          />
        </label>
        {m.isError && (
          <p className="font-data text-micro text-crit">{(m.error as Error).message}</p>
        )}
        <button
          type="submit"
          disabled={m.isPending || !user || !pass}
          className="w-full rounded border border-line bg-bg2 py-2 font-dense text-label uppercase tracking-wide text-ink0 hover:bg-line disabled:opacity-50"
        >
          {m.isPending ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
    </div>
  )
}
