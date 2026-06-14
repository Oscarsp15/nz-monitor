/** Instrumento KPI: label (Condensed) → valor (Mono) → unidad/sublínea (DESIGN §5). */
export function KpiCard({
  label,
  value,
  unit,
  sub,
  loading = false,
}: {
  label: string
  value: string
  unit?: string
  sub?: string
  loading?: boolean
}) {
  return (
    <div className="panel px-4 py-3">
      <div className="th">{label}</div>
      <div className={`mt-1 font-data text-kpi text-ink0 ${loading ? 'opacity-40' : ''}`}>
        {loading ? '···' : value}
        {unit && <span className="ml-1 text-body text-ink2">{unit}</span>}
      </div>
      {sub && <div className="mt-0.5 font-data text-micro text-ink2">{sub}</div>}
    </div>
  )
}
