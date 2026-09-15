import { AlertTriangle } from 'lucide-react'
import { useEffect, useState } from 'react'

import { SESSION_EXPIRED_EVENT } from '../lib/api'

/**
 * Un 401 a mitad de una acción no debe recargar en silencio (AGENTS §12): se perdería lo
 * que el usuario estaba tecleando sin explicación. `lib/api.ts` avisa con un evento global;
 * esta pantalla lo muestra y deja que el propio usuario decida cuándo volver a entrar.
 */
export function SessionExpiredModal() {
  const [show, setShow] = useState(false)

  useEffect(() => {
    const onExpired = () => setShow(true)
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired)
  }, [])

  if (!show) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="panel w-full max-w-sm space-y-3 p-6 text-center">
        <AlertTriangle size={22} strokeWidth={1.5} className="mx-auto text-warn" />
        <p className="text-body text-ink0">Tu sesión caducó.</p>
        <p className="font-data text-micro text-ink2">
          Vuelve a entrar — lo que no se guardó se perdió.
        </p>
        <button
          onClick={() => location.reload()}
          className="tap44 w-full rounded border border-line bg-bg2 py-2 font-dense text-label uppercase tracking-wide text-ink0 hover:bg-line"
        >
          Entrar de nuevo
        </button>
      </div>
    </div>
  )
}
