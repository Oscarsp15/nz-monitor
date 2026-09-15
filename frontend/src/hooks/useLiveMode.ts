import { useEffect, useRef, useState } from 'react'

import { useAuth } from '../lib/auth'

/**
 * "Modo en vivo" acotado por-vista (AGENTS §2.3, §8): refresca SOLO esta vista cada
 * `intervalMs` mientras está activo Y la pestaña visible. Off por defecto. Nunca es global.
 * `viewer` no puede activarlo (mismo límite que "Actualizar ahora" — ver RefreshButton).
 */
export function useLiveMode(onTick: () => void, intervalMs = 20_000) {
  const { isOperador } = useAuth()
  const [liveState, setLiveState] = useState(false)
  const live = liveState && isOperador
  const cb = useRef(onTick)
  cb.current = onTick

  const setLive = (v: boolean) => {
    if (!isOperador) return // viewer: sin consultas en vivo
    setLiveState(v)
  }

  useEffect(() => {
    if (!live) return
    let timer: number | undefined
    const start = () => {
      stop()
      timer = window.setInterval(() => {
        if (document.visibilityState === 'visible') cb.current()
      }, intervalMs)
    }
    const stop = () => {
      if (timer) window.clearInterval(timer)
    }
    const onVis = () => (document.visibilityState === 'visible' ? start() : stop())
    start()
    document.addEventListener('visibilitychange', onVis)
    return () => {
      stop()
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [live, intervalMs])

  return { live, setLive, allowed: isOperador }
}
