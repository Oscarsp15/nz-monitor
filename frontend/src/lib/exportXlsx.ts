import * as XLSX from 'xlsx'

export interface Col<T> {
  header: string
  value: (row: T) => string | number
}

/** Exporta filas a un .xlsx real (igual que el v1, librería SheetJS). */
export function exportToExcel<T>(filename: string, rows: T[], cols: Col<T>[], sheet = 'Datos') {
  const aoa = [cols.map((c) => c.header), ...rows.map((r) => cols.map((c) => c.value(r)))]
  const ws = XLSX.utils.aoa_to_sheet(aoa)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, sheet)
  XLSX.writeFile(wb, filename)
}

/** Marca de tiempo corta para nombres de archivo (sin Date.now en SSR; aquí es cliente). */
export function stamp(): string {
  return new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-')
}
