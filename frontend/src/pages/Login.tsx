import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Activity } from 'lucide-react'
import { useState } from 'react'

import { api, setToken } from '../lib/api'

function friendly(err: unknown): string {
  const msg = (err as Error).message ?? ''
  if (msg.startsWith('401')) return 'Usuario o contraseña incorrectos.'
  return msg || 'No se pudo iniciar sesión.'
}

export function Login() {
  const qc = useQueryClient()
  const [user, setUser] = useState('')
  const [pass, setPass] = useState('')
  const m = useMutation({
    mutationFn: () => api.login(user, pass),
    onSuccess: (r) => {
      setToken(r.token)
      // refresca el contexto de sesión sin recargar toda la app (feedback instantáneo)
      qc.invalidateQueries({ queryKey: ['auth'] })
    },
  })

  return (
    <div className="min-h-app flex items-center justify-center bg-bg0 px-4">
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
            className="tap44 mt-1 w-full rounded border border-line bg-bg1 px-3 py-2 font-data text-body text-ink0"
          />
        </label>
        <label className="block">
          <span className="th">Contraseña</span>
          <input
            type="password"
            value={pass}
            onChange={(e) => setPass(e.target.value)}
            className="tap44 mt-1 w-full rounded border border-line bg-bg1 px-3 py-2 font-data text-body text-ink0"
          />
        </label>
        {m.isError && <p className="font-data text-micro text-crit">{friendly(m.error)}</p>}
        <button
          type="submit"
          disabled={m.isPending || !user || !pass}
          className="tap44 w-full rounded border border-line bg-bg2 py-2 font-dense text-label uppercase tracking-wide text-ink0 hover:bg-line disabled:opacity-50"
        >
          {m.isPending ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
    </div>
  )
}
