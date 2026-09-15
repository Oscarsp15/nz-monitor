import { useEffect } from 'react'

/**
 * Explicación breve y accesible al tocar (no un `title` que en táctil nunca aparece) para una
 * acción que el rol actual no puede hacer. `aria-live` para lectores de pantalla; se retira sola.
 */
export function BlockedHint({
  show,
  onDone,
  message = 'Tu rol no permite consultas en vivo — no puedes abrir el detalle de una tabla.',
}: {
  show: boolean
  onDone: () => void
  message?: string
}) {
  useEffect(() => {
    if (!show) return
    const t = setTimeout(onDone, 4000)
    return () => clearTimeout(t)
  }, [show, onDone])

  if (!show) return null

  return (
    <p
      role="status"
      aria-live="polite"
      className="rounded border border-line bg-bg2 px-3 py-2 font-data text-micro text-ink1"
    >
      {message}
    </p>
  )
}
