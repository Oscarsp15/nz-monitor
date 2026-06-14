import { useQuery } from '@tanstack/react-query'
import { type ReactNode } from 'react'

import { api } from '../lib/api'
import { Login } from '../pages/Login'

/** Si hay login configurado y no estás autenticado, muestra el Login; si no, la app. */
export function AuthGate({ children }: { children: ReactNode }) {
  const q = useQuery({ queryKey: ['auth', 'status'], queryFn: api.authStatus, retry: false })
  if (q.isLoading) {
    return <div className="flex min-h-screen items-center justify-center bg-bg0 text-ink2">…</div>
  }
  if (q.data && q.data.configured && !q.data.authenticated) {
    return <Login />
  }
  return <>{children}</>
}
