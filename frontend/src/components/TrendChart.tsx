// Gráfico de tendencia minimalista en SVG (sin dependencias, estilo "instrumento").

export function TrendChart({ values, color = 'var(--live)' }: { values: number[]; color?: string }) {
  if (values.length < 2) {
    return (
      <div className="flex h-16 items-center justify-center font-data text-micro text-ink2">
        recolectando datos…
      </div>
    )
  }
  const W = 100
  const H = 32
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * W
    const y = H - 3 - ((v - min) / range) * (H - 6) // padding vertical 3
    return [x, y] as const
  })
  const line = pts.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join(' ')
  const area = `0,${H} ${line} ${W},${H}`
  const last = pts[pts.length - 1]
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="h-16 w-full">
      <polygon points={area} fill={color} opacity={0.12} />
      <polyline
        points={line}
        fill="none"
        stroke={color}
        strokeWidth={1.25}
        vectorEffect="non-scaling-stroke"
      />
      <circle cx={last[0]} cy={last[1]} r={1.6} fill={color} vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

/** Panel de tendencia: etiqueta, valor actual grande, gráfico y rango min–máx. */
export function TrendPanel({
  label,
  current,
  values,
  color,
  footer,
}: {
  label: string
  current: string
  values: number[]
  color?: string
  footer?: string
}) {
  return (
    <div className="panel px-4 py-3">
      <div className="flex items-baseline justify-between">
        <span className="th">{label}</span>
        <span className="font-data text-body text-ink0">{current}</span>
      </div>
      <div className="mt-2">
        <TrendChart values={values} color={color} />
      </div>
      {footer && <div className="mt-1 font-data text-micro text-ink2">{footer}</div>}
    </div>
  )
}
