import { useEffect, useRef, useState } from 'react'

/**
 * "Modo en vivo" acotado por-vista (AGENTS §2.3, §8): refresca SOLO esta vista cada
 * `intervalMs` mientras está activo Y la pestaña visible. Off por defecto. Nunca es global.
 */
export function useLiveMode(onTick: () => void, intervalMs = 20_000) {
  const [live, setLive] = useState(false)
  const cb = useRef(onTick)
  cb.current = onTick

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

  return { live, setLive }
}
