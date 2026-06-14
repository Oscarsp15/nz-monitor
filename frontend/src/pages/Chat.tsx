import { useMutation } from '@tanstack/react-query'
import { Send, Sparkles } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { api } from '../lib/api'

interface Msg {
  role: 'user' | 'assistant'
  content: string
}

const SUGERENCIAS = [
  'Top 10 tablas que necesitan mejor distribución',
  '¿Qué dataslice está más saturado y qué tablas lo cargan?',
  '¿Qué tablas puedo dropear en DESA_MODELOS?',
]

export function Chat() {
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  const send = useMutation({
    mutationFn: (history: Msg[]) => api.aiChat(history),
    onSuccess: (r) =>
      setMsgs((m) => [...m, { role: 'assistant', content: r.error || r.answer || '—' }]),
    onError: (e) => setMsgs((m) => [...m, { role: 'assistant', content: `Error: ${(e as Error).message}` }]),
  })

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs, send.isPending])

  const submit = (text: string) => {
    const t = text.trim()
    if (!t || send.isPending) return
    const next: Msg[] = [...msgs, { role: 'user', content: t }]
    setMsgs(next)
    setInput('')
    send.mutate(next)
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-7.5rem)] max-w-3xl flex-col md:h-[calc(100vh-5rem)]">
      <div className="mb-3">
        <h1 className="font-dense text-lg font-semibold text-ink0">Asistente</h1>
        <p className="text-body text-ink1">
          Pregunta sobre tu Netezza — consulta los datos en vivo (skew, espacio, dataslices,
          actividad).
        </p>
      </div>

      {/* Mensajes */}
      <div className="panel flex-1 space-y-3 overflow-y-auto p-4">
        {msgs.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
            <Sparkles size={26} strokeWidth={1.4} className="text-live" />
            <p className="text-body text-ink1">Hazme una pregunta. Por ejemplo:</p>
            <div className="flex flex-col gap-2">
              {SUGERENCIAS.map((s) => (
                <button
                  key={s}
                  onClick={() => submit(s)}
                  className="rounded border border-line px-3 py-1.5 text-body text-ink1 hover:bg-bg2 hover:text-ink0"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] whitespace-pre-wrap rounded px-3 py-2 text-body ${
                m.role === 'user'
                  ? 'bg-bg2 text-ink0'
                  : 'border border-line bg-bg1 font-data text-ink0'
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}
        {send.isPending && (
          <div className="flex justify-start">
            <div className="rounded border border-line bg-bg1 px-3 py-2 font-data text-body text-ink2">
              consultando Netezza…
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Entrada */}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          submit(input)
        }}
        className="mt-3 flex items-center gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Escribe tu pregunta…"
          className="flex-1 rounded border border-line bg-bg1 px-3 py-2 text-body text-ink0 placeholder:text-ink2"
        />
        <button
          type="submit"
          disabled={send.isPending || !input.trim()}
          className="inline-flex items-center gap-1.5 rounded border border-line bg-bg2 px-3 py-2 font-dense text-label uppercase tracking-wide text-ink0 hover:bg-line disabled:opacity-50"
        >
          <Send size={14} strokeWidth={1.6} /> Enviar
        </button>
      </form>
    </div>
  )
}
