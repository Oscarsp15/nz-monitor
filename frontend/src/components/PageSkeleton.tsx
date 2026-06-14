// Esqueleto atenuado para carga ATÓMICA (AGENTS §8/§12): se muestra mientras TODAS las
// consultas de la vista cargan, para luego pintar el contenido junto (con .reveal).
export function PageSkeleton({ kpis = 3, panels = 1 }: { kpis?: number; panels?: number }) {
  return (
    <div className="space-y-4">
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
