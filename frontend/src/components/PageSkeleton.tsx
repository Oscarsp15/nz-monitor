// Esqueleto atenuado para carga ATÓMICA (AGENTS §8/§12): se muestra mientras TODAS las
// consultas de la vista cargan, para luego pintar el contenido junto (con .reveal).
// Revalidación visible (§2.1): si no hay valor previo que pintar, este esqueleto lleva el
// mismo mensaje "actualizando…" que el sello de frescura — nunca queda en blanco sin decir nada.
export function PageSkeleton({
  kpis = 3,
  panels = 1,
  message = 'actualizando…',
}: {
  kpis?: number
  panels?: number
  message?: string
}) {
  return (
    <div className="space-y-4">
      <p className="flex items-center gap-1.5 font-data text-micro text-ink2">
        <span className="h-1.5 w-1.5 rounded-pill bg-live pulse-live" aria-hidden />
        {message}
      </p>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {Array.from({ length: kpis }).map((_, i) => (
          <div key={i} className="panel h-[72px] animate-pulse opacity-40" />
        ))}
      </div>
      {Array.from({ length: panels }).map((_, i) => (
        <div key={i} className="panel h-56 animate-pulse opacity-40" />
      ))}
    </div>
  )
}
