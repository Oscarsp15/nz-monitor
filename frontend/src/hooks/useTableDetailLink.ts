import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../lib/auth'

/**
 * Enlace al detalle de una tabla: `/api/table` y `/api/table/slices` son consultas en vivo al
 * appliance (la de historial es la más cara de toda la app) y el backend las exige operador+.
 * Para `viewer` no navega — deja la fila igual de tocable (44px) y explica por qué al tocarla,
 * no solo con un `title` que en táctil nadie ve (DESIGN §9.2).
 */
export function useTableDetailLink() {
  const navigate = useNavigate()
  const { isOperador } = useAuth()
  const [blocked, setBlocked] = useState(false)

  const open = (objid: number, table: string | null) => {
    if (!isOperador) {
      setBlocked(true)
      return
    }
    navigate(`/tabla/${objid}?name=${encodeURIComponent(table ?? '')}`)
  }

  return { open, allowed: isOperador, blocked, dismissBlocked: () => setBlocked(false) }
}
