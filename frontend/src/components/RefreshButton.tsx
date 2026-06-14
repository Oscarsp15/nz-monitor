import { RotateCw } from 'lucide-react'

/** Botón "Actualizar ahora": fuerza query real (fresh=true) saltando la caché (AGENTS §8). */
export function RefreshButton({
  onClick,
  busy = false,
}: {
  onClick: () => void
  busy?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={busy}
      className="inline-flex items-center gap-1.5 rounded border border-line px-2.5 py-1 font-dense text-label uppercase tracking-wide text-ink1 hover:bg-bg2 hover:text-ink0 disabled:opacity-50"
    >
      <RotateCw size={13} strokeWidth={1.5} className={busy ? 'animate-spin' : ''} />
      Actualizar ahora
    </button>
  )
}
