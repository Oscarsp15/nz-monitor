import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Send } from 'lucide-react'
import { useEffect, useState } from 'react'

import { PageSkeleton } from '../components/PageSkeleton'
import { StatusPill } from '../components/StatusPill'
import { api } from '../lib/api'

export function Settings() {
  const qc = useQueryClient()
  const cfg = useQuery({ queryKey: ['settings', 'telegram'], queryFn: api.getTelegram })

  const ai = useQuery({ queryKey: ['settings', 'ai'], queryFn: api.getAi })
  const sftp = useQuery({ queryKey: ['settings', 'sftp'], queryFn: api.getSftp })

  const [chatId, setChatId] = useState('')
  const [token, setToken] = useState('')
  const [testMsg, setTestMsg] = useState<string | null>(null)

  const [aiKey, setAiKey] = useState('')
  const [aiModel, setAiModel] = useState('')
  const [aiEnabled, setAiEnabled] = useState(false)
  const [aiAssistant, setAiAssistant] = useState(false)
  const [aiMsg, setAiMsg] = useState<string | null>(null)

  const [sHost, setSHost] = useState('')
  const [sPort, setSPort] = useState(22)
  const [sUser, setSUser] = useState('')
  const [sPass, setSPass] = useState('')
  const [sDef, setSDef] = useState('/')
  const [sMsg, setSMsg] = useState<string | null>(null)

  useEffect(() => {
    if (cfg.data) setChatId(cfg.data.chat_id)
  }, [cfg.data])

  useEffect(() => {
    if (ai.data) {
      setAiModel(ai.data.model)
      setAiEnabled(ai.data.enabled)
      setAiAssistant(ai.data.assistant)
    }
  }, [ai.data])

  const saveAi = useMutation({
    mutationFn: () =>
      api.saveAi({
        api_key: aiKey || undefined,
        model: aiModel,
        enabled: aiEnabled,
        assistant: aiAssistant,
      }),
    onSuccess: () => {
      setAiKey('')
      qc.invalidateQueries({ queryKey: ['settings', 'ai'] })
    },
  })
  const testAi = useMutation({
    mutationFn: api.testAi,
    onMutate: () => setAiMsg(null),
    onSuccess: (r) =>
      setAiMsg(r.ok ? `✅ IA OK: "${r.sample ?? ''}"` : '❌ La IA no respondió (revisa la API key).'),
    onError: (e) => setAiMsg(`❌ ${(e as Error).message}`),
  })

  useEffect(() => {
    if (sftp.data) {
      setSHost(sftp.data.host)
      setSPort(sftp.data.port)
      setSUser(sftp.data.user)
      setSDef(sftp.data.default_path || '/')
    }
  }, [sftp.data])

  const saveSftp = useMutation({
    mutationFn: () =>
      api.saveSftp({
        host: sHost,
        port: sPort,
        user: sUser,
        password: sPass || undefined,
        default_path: sDef,
      }),
    onSuccess: () => {
      setSPass('')
      qc.invalidateQueries({ queryKey: ['settings', 'sftp'] })
    },
  })
  const testSftp = useMutation({
    mutationFn: api.testSftp,
    onMutate: () => setSMsg(null),
    onSuccess: (r) =>
      setSMsg(r.status === 'connected' ? '✅ Conectado al SFTP.' : `❌ ${r.error || 'no conecta'}`),
    onError: (e) => setSMsg(`❌ ${(e as Error).message}`),
  })

  const save = useMutation({
    mutationFn: () => api.saveTelegram({ chat_id: chatId, bot_token: token || undefined }),
    onSuccess: () => {
      setToken('')
      qc.invalidateQueries({ queryKey: ['settings', 'telegram'] })
      qc.invalidateQueries({ queryKey: ['mon', 'alerts'] })
    },
  })

  const test = useMutation({
    mutationFn: api.testTelegram,
    onMutate: () => setTestMsg(null),
    onSuccess: (r) =>
      setTestMsg(r.ok ? '✅ Mensaje enviado. Revisa Telegram.' : '❌ No se pudo enviar (revisa token/chat_id).'),
    onError: (e) => setTestMsg(`❌ ${(e as Error).message}`),
  })

  if (cfg.isLoading) {
    return (
      <div className="space-y-4">
        <h1 className="font-dense text-lg font-semibold text-ink0">Ajustes</h1>
        <PageSkeleton kpis={0} panels={1} />
      </div>
    )
  }

  return (
    <div className="reveal max-w-2xl space-y-5">
      <div>
        <h1 className="font-dense text-lg font-semibold text-ink0">Ajustes</h1>
        <p className="text-body text-ink1">Toda la configuración vive aquí (se guarda cifrada).</p>
      </div>

      <section className="panel overflow-hidden">
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <h2 className="th">Alertas por Telegram</h2>
          <StatusPill status={cfg.data?.configured ? 'ok' : 'empty'} />
        </div>

        <div className="space-y-4 p-4">
          <p className="text-body text-ink1">
            Recibe un mensaje cuando un dataslice entra en <span className="text-crit">crítico</span>{' '}
            (≥95%). Funciona con un chat personal, un <b>grupo</b> (id negativo) o un canal.
          </p>

          <label className="block">
            <span className="th">Bot token</span>
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder={cfg.data?.has_token ? '•••••••• (guardado — escribe para cambiarlo)' : '123456:ABC-DEF…'}
              className="mt-1 w-full rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0 placeholder:text-ink2"
            />
            <span className="mt-1 block font-data text-micro text-ink2">
              Créalo con @BotFather en Telegram.
            </span>
          </label>

          <label className="block">
            <span className="th">Chat ID (usuario, grupo o canal)</span>
            <input
              value={chatId}
              onChange={(e) => setChatId(e.target.value)}
              placeholder="-1001234567890"
              className="mt-1 w-full rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0 placeholder:text-ink2"
            />
          </label>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => save.mutate()}
              disabled={save.isPending}
              className="rounded border border-line bg-bg2 px-3 py-1.5 font-dense text-label uppercase tracking-wide text-ink0 hover:bg-line disabled:opacity-50"
            >
              {save.isPending ? 'Guardando…' : 'Guardar'}
            </button>
            <button
              onClick={() => test.mutate()}
              disabled={test.isPending || !cfg.data?.configured}
              className="inline-flex items-center gap-1.5 rounded border border-line px-3 py-1.5 font-dense text-label uppercase tracking-wide text-ink1 hover:bg-bg2 hover:text-ink0 disabled:opacity-50"
              title={cfg.data?.configured ? 'Enviar mensaje de prueba' : 'Guarda token y chat_id primero'}
            >
              <Send size={13} strokeWidth={1.5} /> Probar
            </button>
            {save.isSuccess && !save.isPending && (
              <span className="font-data text-micro text-ok">Guardado.</span>
            )}
            {testMsg && <span className="font-data text-micro text-ink1">{testMsg}</span>}
          </div>
        </div>
      </section>

      <section className="panel overflow-hidden">
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <h2 className="th">Alertas inteligentes (IA · Groq)</h2>
          <StatusPill status={ai.data?.enabled && ai.data?.has_key ? 'ok' : 'empty'} />
        </div>
        <div className="space-y-4 p-4">
          <p className="text-body text-ink1">
            <b>Opcional.</b> Añade al aviso una recomendación IA: qué tablas saturan el dataslice y
            qué hacer (redistribuir / GROOM / DROP). Requiere una API key de Groq.
          </p>

          <label className="flex cursor-pointer items-center gap-2 text-body text-ink0">
            <input
              type="checkbox"
              checked={aiEnabled}
              onChange={(e) => setAiEnabled(e.target.checked)}
              className="accent-[var(--live)]"
            />
            Activar análisis IA en las alertas
          </label>

          <label className="flex cursor-pointer items-center gap-2 text-body text-ink0">
            <input
              type="checkbox"
              checked={aiAssistant}
              onChange={(e) => setAiAssistant(e.target.checked)}
              className="accent-[var(--live)]"
            />
            Responder mis mensajes (chat por Telegram)
          </label>
          <p className="font-data text-micro text-ink2">
            Responde a tus mensajes en Telegram (responde a una alerta del bot para preguntarle sobre
            ella). Solo atiende tu chat configurado.
          </p>

          <label className="block">
            <span className="th">Groq API key</span>
            <input
              type="password"
              value={aiKey}
              onChange={(e) => setAiKey(e.target.value)}
              placeholder={ai.data?.has_key ? '•••••••• (guardada — escribe para cambiarla)' : 'gsk_…'}
              className="mt-1 w-full rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0 placeholder:text-ink2"
            />
          </label>

          <label className="block">
            <span className="th">Modelo</span>
            <input
              value={aiModel}
              onChange={(e) => setAiModel(e.target.value)}
              placeholder="llama-3.3-70b-versatile"
              className="mt-1 w-full rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0 placeholder:text-ink2"
            />
          </label>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => saveAi.mutate()}
              disabled={saveAi.isPending}
              className="rounded border border-line bg-bg2 px-3 py-1.5 font-dense text-label uppercase tracking-wide text-ink0 hover:bg-line disabled:opacity-50"
            >
              {saveAi.isPending ? 'Guardando…' : 'Guardar'}
            </button>
            <button
              onClick={() => testAi.mutate()}
              disabled={testAi.isPending || !ai.data?.has_key}
              className="inline-flex items-center gap-1.5 rounded border border-line px-3 py-1.5 font-dense text-label uppercase tracking-wide text-ink1 hover:bg-bg2 hover:text-ink0 disabled:opacity-50"
            >
              Probar IA
            </button>
            {aiMsg && <span className="font-data text-micro text-ink1">{aiMsg}</span>}
          </div>
        </div>
      </section>

      <section className="panel overflow-hidden">
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <h2 className="th">Conexión SFTP</h2>
          <StatusPill status={sftp.data?.configured ? 'ok' : 'empty'} />
        </div>
        <div className="space-y-4 p-4">
          <p className="text-body text-ink1">
            Servidor SSH/SFTP para el monitor de disco y archivos viejos.
          </p>
          <div className="flex flex-wrap gap-3">
            <label className="flex flex-col gap-1">
              <span className="th">Host</span>
              <input
                value={sHost}
                onChange={(e) => setSHost(e.target.value)}
                placeholder="10.0.0.1"
                className="w-48 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0 placeholder:text-ink2"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="th">Puerto</span>
              <input
                type="number"
                value={sPort}
                onChange={(e) => setSPort(Number(e.target.value) || 22)}
                className="w-24 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="th">Usuario</span>
              <input
                value={sUser}
                onChange={(e) => setSUser(e.target.value)}
                className="w-40 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="th">Contraseña</span>
              <input
                type="password"
                value={sPass}
                onChange={(e) => setSPass(e.target.value)}
                placeholder={sftp.data?.has_password ? '•••••••• (guardada)' : '••••••••'}
                className="w-48 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0 placeholder:text-ink2"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="th">Ruta por defecto</span>
              <input
                value={sDef}
                onChange={(e) => setSDef(e.target.value)}
                placeholder="/nzscratch/nz"
                className="w-56 rounded border border-line bg-bg1 px-3 py-1.5 font-data text-body text-ink0 placeholder:text-ink2"
              />
            </label>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => saveSftp.mutate()}
              disabled={saveSftp.isPending}
              className="rounded border border-line bg-bg2 px-3 py-1.5 font-dense text-label uppercase tracking-wide text-ink0 hover:bg-line disabled:opacity-50"
            >
              {saveSftp.isPending ? 'Guardando…' : 'Guardar'}
            </button>
            <button
              onClick={() => testSftp.mutate()}
              disabled={testSftp.isPending || !sftp.data?.configured}
              className="rounded border border-line px-3 py-1.5 font-dense text-label uppercase tracking-wide text-ink1 hover:bg-bg2 hover:text-ink0 disabled:opacity-50"
            >
              Probar conexión
            </button>
            {sMsg && <span className="font-data text-micro text-ink1">{sMsg}</span>}
          </div>
        </div>
      </section>

      <section className="panel p-4">
        <h2 className="th">Cómo obtener el Chat ID de un grupo</h2>
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-body text-ink1">
          <li>Crea el bot con <span className="font-data text-ink0">@BotFather</span> y copia el token.</li>
          <li>Agrega el bot a tu grupo.</li>
          <li>Escribe cualquier mensaje en el grupo.</li>
          <li>
            Abre{' '}
            <span className="font-data text-ink0">
              https://api.telegram.org/bot&lt;TOKEN&gt;/getUpdates
            </span>{' '}
            y copia <span className="font-data text-ink0">chat.id</span> (negativo para grupos).
          </li>
        </ol>
      </section>
    </div>
  )
}
