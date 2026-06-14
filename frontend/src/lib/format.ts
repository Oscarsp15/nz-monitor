// Formato de cifras y del sello de frescura ("actualizado hace X").

export function gb(n: number | null | undefined): string {
  if (n == null) return '—'
  if (n >= 1024) return `${(n / 1024).toFixed(2)} TB`
  return `${n.toFixed(2)} GB`
}

export function int(n: number | null | undefined): string {
  if (n == null) return '—'
  return n.toLocaleString('es')
}

/** "hace 12s" / "hace 3 min" / "hace 2 h" a partir de segundos. */
export function ago(seconds: number | null | undefined): string {
  if (seconds == null) return 'sin datos'
  const s = Math.max(0, Math.round(seconds))
  if (s < 60) return `hace ${s}s`
  const m = Math.round(s / 60)
  if (m < 60) return `hace ${m} min`
  const h = Math.round(m / 60)
  if (h < 24) return `hace ${h} h`
  return `hace ${Math.round(h / 24)} d`
}

/** Edad en segundos a partir de un epoch en segundos (campo `at` del backend). */
export function ageFromAt(at: number | null | undefined): number | null {
  if (at == null) return null
  return Date.now() / 1000 - at
}

export type Severity = 'neutral' | 'warn' | 'crit'

/** Umbrales de skew del DESIGN.md §5: <8 neutro · 8–25 warn · >25 crítico. */
export function skewSeverity(skew: number): Severity {
  if (skew > 25) return 'crit'
  if (skew >= 8) return 'warn'
  return 'neutral'
}
