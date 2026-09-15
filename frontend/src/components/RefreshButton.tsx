import { RotateCw } from 'lucide-react'

import { useAuth } from '../lib/auth'

/** Botón "Actualizar ahora": fuerza query real (fresh=true) saltando la caché (AGENTS §8). */
export function RefreshButton({
  onClick,
  busy = false,
}: {
  onClick: () => void
  busy?: boolean
}) {
  const { isOperador } = useAuth()
  const blocked = !isOperador // viewer: no puede forzar consultas en vivo

  return (
    <button
      onClick={blocked ? undefined : onClick}
      disabled={busy || blocked}
      title={blocked ? 'Tu rol no permite consultas en vivo' : undefined}
      className="inline-flex items-center gap-1.5 rounded border border-line px-2.5 py-1 font-dense text-label uppercase tracking-wide text-ink1 hover:bg-bg2 hover:text-ink0 disabled:opacity-50"
    >
      <RotateCw size={13} strokeWidth={1.5} className={busy ? 'animate-spin' : ''} />
      Actualizar ahora
    </button>
  )
}
