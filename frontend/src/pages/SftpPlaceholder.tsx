import { FolderClock, HardDrive } from 'lucide-react'
import { useLocation } from 'react-router-dom'

export function SftpPlaceholder() {
  const { pathname } = useLocation()
  const archivos = pathname.includes('archivos')
  const Icon = archivos ? FolderClock : HardDrive
  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-dense text-lg font-semibold text-ink0">
          {archivos ? 'Archivos viejos' : 'Espacio en disco (SFTP)'}
        </h1>
        <p className="text-body text-ink1">Monitor de servidores SFTP.</p>
      </div>
      <div className="panel flex flex-col items-center justify-center gap-2 px-4 py-16 text-center">
        <Icon size={28} strokeWidth={1.4} className="text-ink2" />
        <p className="text-body text-ink1">Próximamente.</p>
        <p className="font-data text-micro text-ink2">
          {archivos
            ? 'Buscar archivos antiguos para limpieza (por patrón y antigüedad).'
            : 'Uso de disco por carpeta y alertas de espacio.'}
        </p>
      </div>
    </div>
  )
}
