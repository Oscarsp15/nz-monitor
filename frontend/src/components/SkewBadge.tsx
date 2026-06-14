import { skewSeverity } from '../lib/format'

const COLOR = { neutral: 'var(--ink-1)', warn: 'var(--warn)', crit: 'var(--crit)' } as const

/** Skew: número + mini-barra de 4 segmentos que se llena según severidad (DESIGN §5). */
export function SkewBadge({ skew }: { skew: number }) {
  const sev = skewSeverity(skew)
  const c = COLOR[sev]
  // segmentos llenos: 1 (neutro) · 2-3 (warn) · 4 (crit)
  const filled = sev === 'crit' ? 4 : sev === 'warn' ? (skew > 16 ? 3 : 2) : 1
  return (
    <span className="inline-flex items-center justify-end gap-2">
      <span className="num text-body" style={{ color: c }}>
        {skew.toFixed(2)}
      </span>
      <span className="flex gap-0.5" aria-hidden>
        {[0, 1, 2, 3].map((i) => (
          <span
            key={i}
            className="h-3 w-1 rounded-[1px]"
            style={{ background: i < filled ? c : 'var(--line-strong)' }}
          />
        ))}
      </span>
    </span>
  )
}
