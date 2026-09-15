import { ago } from '../lib/format'

/**
 * Sello de frescura: "actualizado hace X" + punto que pulsa en --live si está en vivo.
 * Revalidación visible (AGENTS §2.1): mientras `updating` está activo, el sello avisa que la
 * consulta real está en curso en vez de dejar el dato viejo pasar por actual.
 */
export function FreshnessSeal({
  ageSeconds,
  live = false,
  updating = false,
}: {
  ageSeconds: number | null
  live?: boolean
  updating?: boolean
}) {
  return (
    <span className="inline-flex items-center gap-1.5 font-data text-micro text-ink2">
      <span
        className={`h-1.5 w-1.5 rounded-pill ${live || updating ? 'bg-live pulse-live' : 'bg-ink2'}`}
        aria-hidden
      />
      {updating ? 'actualizando…' : `actualizado ${ago(ageSeconds)}`}
    </span>
  )
}
