import { Search, X } from 'lucide-react'

export function SearchInput({
  value,
  onChange,
  placeholder = 'Buscar…',
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  return (
    <div className="relative">
      <Search
        size={14}
        strokeWidth={1.5}
        className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-ink2"
      />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="tap44 w-48 rounded border border-line bg-bg1 py-1 pl-7 pr-7 font-data text-body text-ink0 placeholder:text-ink2"
      />
      {value && (
        <button
          onClick={() => onChange('')}
          className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-ink2 hover:text-ink0"
          aria-label="Limpiar"
        >
          <X size={13} />
        </button>
      )}
    </div>
  )
}

/** Botón de exportar a Excel (reutilizable). */
export function ExportButton({ onClick, disabled = false }: { onClick: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="tap44 inline-flex items-center justify-center gap-1.5 rounded border border-line px-2.5 py-1 font-dense text-label uppercase tracking-wide text-ink1 hover:bg-bg2 hover:text-ink0 disabled:opacity-50"
    >
      Excel
    </button>
  )
}
