import { ago } from '../lib/format'

/** Sello de frescura: "actualizado hace X" + punto que pulsa en --live si está en vivo. */
export function FreshnessSeal({
  ageSeconds,
  live = false,
}: {
  ageSeconds: number | null
  live?: boolean
}) {
  return (
    <span className="inline-flex items-center gap-1.5 font-data text-micro text-ink2">
      <span
        className={`h-1.5 w-1.5 rounded-pill ${live ? 'bg-live pulse-live' : 'bg-ink2'}`}
        aria-hidden
      />
      actualizado {ago(ageSeconds)}
    </span>
  )
}
