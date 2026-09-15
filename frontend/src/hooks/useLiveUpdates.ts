import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'

import { getToken } from '../lib/api'

/**
 * Suscripción SSE a /api/stream: cuando el recolector escribe un snapshot nuevo, la API empuja
 * un evento y refrescamos las vistas pasivas (sin polling de cliente). EventSource reconecta solo.
 * EventSource no admite cabeceras, asi que el token de sesion viaja por query string (la API
 * lo acepta solo en esta ruta).
 */
export function useLiveUpdates() {
  const qc = useQueryClient()
  useEffect(() => {
    const token = getToken()
    if (!token) return
    const es = new EventSource(`/api/stream?token=${encodeURIComponent(token)}`)
    es.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data)
        if (Array.isArray(d.changed) && d.changed.length) {
          qc.invalidateQueries({ queryKey: ['mon'] })
          qc.invalidateQueries({ queryKey: ['hist'] })
          qc.invalidateQueries({ queryKey: ['dataslices'] })
        }
      } catch {
        /* keepalive / hello: ignorar */
      }
    }
    return () => es.close()
  }, [qc])
}
