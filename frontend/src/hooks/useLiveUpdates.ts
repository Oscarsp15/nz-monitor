import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'

/**
 * Suscripción SSE a /api/stream: cuando el recolector escribe un snapshot nuevo, la API empuja
 * un evento y refrescamos las vistas pasivas (sin polling de cliente). EventSource reconecta solo.
 */
export function useLiveUpdates() {
  const qc = useQueryClient()
  useEffect(() => {
    const es = new EventSource('/api/stream')
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
