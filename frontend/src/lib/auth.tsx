import { useQuery, useQueryClient } from '@tanstack/react-query'
import { createContext, useContext, type ReactNode } from 'react'

import { api, clearToken, type Role } from './api'

interface AuthCtx {
  /** true mientras se resuelve /auth/status (+ /auth/me si hay sesión). */
  isLoading: boolean
  authenticated: boolean
  user: string | null
  /** id numérico del usuario (de /auth/me) — comparar "soy yo" por id, no por username. */
  userId: number | null
  role: Role | null
  isAdmin: boolean
  isOperador: boolean
  mustChangePassword: boolean
  logout: () => void
}

const Ctx = createContext<AuthCtx | null>(null)

/** Sesión + rol, sobre TanStack Query (/auth/status + /auth/me). Login siempre obligatorio. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient()

  const status = useQuery({ queryKey: ['auth', 'status'], queryFn: api.authStatus, retry: false })
  const me = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: api.me,
    enabled: !!status.data?.authenticated,
    retry: false,
  })

  const authenticated = !!status.data?.authenticated
  const role = me.data?.role ?? status.data?.role ?? null
  const user = me.data?.username ?? status.data?.user ?? null
  const userId = me.data?.id ?? null
  const mustChangePassword = me.data?.must_change_password ?? status.data?.must_change_password ?? false

  const logout = () => {
    clearToken()
    qc.clear()
    location.reload() // vuelve a Login limpio
  }

  const value: AuthCtx = {
    isLoading: status.isLoading || (authenticated && me.isLoading),
    authenticated,
    user,
    userId,
    role,
    isAdmin: role === 'admin',
    // isOperador: operador tiene los permisos de operador Y de admin (jerarquía viewer < operador < admin)
    isOperador: role === 'operador' || role === 'admin',
    mustChangePassword,
    logout,
  }

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAuth(): AuthCtx {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useAuth fuera de AuthProvider')
  return ctx
}
