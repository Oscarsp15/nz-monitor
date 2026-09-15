import { type ReactNode } from 'react'

import { useAuth } from '../lib/auth'
import { ChangePassword } from '../pages/ChangePassword'
import { Login } from '../pages/Login'

/**
 * Login SIEMPRE obligatorio (ya no hay "modo abierto"). Sin sesión → Login; con
 * must_change_password → pantalla forzada de cambio de contraseña, sin salida a otra ruta.
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const { isLoading, authenticated, mustChangePassword } = useAuth()

  if (isLoading) {
    return <div className="flex min-h-screen items-center justify-center bg-bg0 text-ink2">…</div>
  }
  if (!authenticated) {
    return <Login />
  }
  if (mustChangePassword) {
    return <ChangePassword />
  }
  return <>{children}</>
}
