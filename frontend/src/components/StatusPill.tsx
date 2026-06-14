type Kind = 'ok' | 'warn' | 'crit' | 'info'

const MAP: Record<string, { kind: Kind; label: string }> = {
  ok: { kind: 'ok', label: 'conectado' },
  connected: { kind: 'ok', label: 'conectado' },
  stale: { kind: 'warn', label: 'degradado' },
  error: { kind: 'crit', label: 'caído' },
  empty: { kind: 'info', label: 'sin datos' },
}

const COLOR: Record<Kind, string> = {
  ok: 'var(--ok)',
  warn: 'var(--warn)',
  crit: 'var(--crit)',
  info: 'var(--info)',
}

/** Pill de estado: punto + texto, color semántico, fondo al 12% (DESIGN §5). */
export function StatusPill({ status }: { status: string }) {
  const { kind, label } = MAP[status] ?? { kind: 'info' as Kind, label: status }
  const c = COLOR[kind]
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-pill px-2 py-0.5 font-data text-micro"
      style={{ color: c, background: `color-mix(in srgb, ${c} 12%, transparent)` }}
    >
      <span className="h-1.5 w-1.5 rounded-pill" style={{ background: c }} aria-hidden />
      {label}
    </span>
  )
}
