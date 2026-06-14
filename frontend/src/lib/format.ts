// Formato de cifras y del sello de frescura ("actualizado hace X").

/** Coacciona a número (el backend a veces manda NUMERIC como string). */
function num(n: number | string | null | undefined): number | null {
  if (n == null || n === '') return null
  const v = typeof n === 'number' ? n : Number(n)
  return Number.isFinite(v) ? v : null
}

export function gb(n: number | string | null | undefined): string {
  const v = num(n)
  if (v == null) return '—'
  if (v >= 1024) return `${(v / 1024).toFixed(2)} TB`
  return `${v.toFixed(2)} GB`
}

export function int(n: number | string | null | undefined): string {
  const v = num(n)
  if (v == null) return '—'
  return v.toLocaleString('es')
}

export function fixed(n: number | string | null | undefined, d = 2): string {
  const v = num(n)
  return v == null ? '—' : v.toFixed(d)
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

/** Formatea timestamps crudos de Netezza ("2026-06-13 16:51:18.000000") a "2026-06-13 16:51". */
export function dt(s: string | null | undefined): string {
  if (!s) return '—'
  const m = String(s).match(/(\d{4}-\d{2}-\d{2})[ T]?(\d{2}:\d{2})?/)
  if (!m) return String(s)
  return m[2] ? `${m[1]} ${m[2]}` : m[1]
}

export type Severity = 'neutral' | 'warn' | 'crit'

/** Umbrales de skew del DESIGN.md §5: <8 neutro · 8–25 warn · >25 crítico. */
export function skewSeverity(skew: number): Severity {
  if (skew > 25) return 'crit'
  if (skew >= 8) return 'warn'
  return 'neutral'
}
