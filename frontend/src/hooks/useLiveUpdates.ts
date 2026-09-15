import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'

import { getToken } from '../lib/api'

/**
 * Suscripción SSE a /api/stream: cuando el recolector escribe un snapshot nuevo, la API empuja
 * un evento y refrescamos las vistas pasivas (sin polling de cliente). EventSource reconecta solo.
 * EventSource no admite cabeceras, asi que el token de sesion viaja por query string (la API
 * lo acepta solo en esta ruta).
 *
 * Petición duplicada al entrar (medido): el generador SSE del backend arranca su tabla de
 * "último visto" vacía en cada conexión nueva, así que su primer barrido (justo tras el saludo
 * `hello`, sin espera) siempre marca como "cambiado" todo snapshot ya existente — aunque nada
 * cambió realmente desde que esta pestaña montó y pidió esos mismos datos hace un instante.
 * Ese primer aviso duplica en el acto el fetch de montaje (space/health/alerts/history…).
 * Se ignora aquí: los avisos genuinos (recolector real) llegan después, nunca en el primer mensaje.
 */
export function useLiveUpdates() {
  const qc = useQueryClient()
  useEffect(() => {
    const token = getToken()
    if (!token) return
    const es = new EventSource(`/api/stream?token=${encodeURIComponent(token)}`)
    let firstChanged = true
    es.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data)
        if (Array.isArray(d.changed) && d.changed.length) {
          if (firstChanged) {
            firstChanged = false
            return // eco de conexión — ver comentario arriba
          }
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
