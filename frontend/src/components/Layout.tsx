import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  Bell,
  Database,
  FolderTree,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Settings as SettingsIcon,
  Users as UsersIcon,
  type LucideIcon,
} from 'lucide-react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'

import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useLiveUpdates } from '../hooks/useLiveUpdates'
import { ThemeToggle } from './ThemeToggle'

interface SubTab {
  to: string
  label: string
}
interface Domain {
  key: string
  label: string
  icon: LucideIcon
  to: string // ruta por defecto del dominio
  prefixes: string[] // rutas que pertenecen a este dominio
  subtabs: SubTab[]
  adminOnly?: boolean
}

const DOMAINS: Domain[] = [
  { key: 'resumen', label: 'Resumen', icon: LayoutDashboard, to: '/', prefixes: [], subtabs: [] },
  {
    key: 'netezza',
    label: 'Netezza',
    icon: Database,
    to: '/tablas',
    prefixes: ['/tablas', '/owners', '/dataslices', '/tabla/', '/dataslice/'],
    subtabs: [
      { to: '/tablas', label: 'Tablas' },
      { to: '/owners', label: 'Owners' },
      { to: '/dataslices', label: 'Dataslices' },
    ],
  },
  {
    key: 'sftp',
    label: 'SFTP',
    icon: FolderTree,
    to: '/sftp/disco',
    prefixes: ['/sftp'],
    subtabs: [
      { to: '/sftp/disco', label: 'Disco' },
      { to: '/sftp/archivos', label: 'Archivos viejos' },
    ],
  },
  { key: 'alertas', label: 'Alertas', icon: Bell, to: '/alertas', prefixes: ['/alertas'], subtabs: [] },
  {
    key: 'usuarios',
    label: 'Usuarios',
    icon: UsersIcon,
    to: '/usuarios',
    prefixes: ['/usuarios'],
    subtabs: [],
    adminOnly: true,
  },
  {
    key: 'ajustes',
    label: 'Ajustes',
    icon: SettingsIcon,
    to: '/ajustes',
    prefixes: ['/ajustes'],
    subtabs: [],
    adminOnly: true,
  },
]

const ROLE_LABEL: Record<string, string> = { admin: 'Administrador', operador: 'Operador', viewer: 'Visor' }

function activeDomain(path: string, domains: Domain[]): Domain {
  if (path === '/') return domains[0]
  return domains.find((d) => d.prefixes.some((p) => path.startsWith(p))) ?? domains[0]
}

function useAlertCount(): { count: number; crit: boolean } {
  const q = useQuery({ queryKey: ['mon', 'alerts'], queryFn: api.monitoringAlerts })
  const alerts = q.data?.data?.alerts ?? []
  return { count: alerts.length, crit: alerts.some((a) => a.level === 'crit') }
}

function Badge({ count, crit }: { count: number; crit: boolean }) {
  if (!count) return null
  return (
    <span
      className="absolute -right-1 -top-1 flex h-3.5 min-w-3.5 items-center justify-center rounded-pill px-1 font-data text-[9px] text-bg0"
      style={{ background: crit ? 'var(--crit)' : 'var(--warn)' }}
    >
      {count}
    </span>
  )
}

export function Layout() {
  const { pathname } = useLocation()
  const { user, role, isAdmin, logout } = useAuth()
  const domains = DOMAINS.filter((d) => !d.adminOnly || isAdmin)
  const dom = activeDomain(pathname, domains)
  const alert = useAlertCount()
  useLiveUpdates() // SSE: refresca las vistas cuando el recolector publica datos nuevos

  return (
    <div className="min-h-screen md:flex">
      {/* Sidebar (desktop) — nivel 1 */}
      <aside className="sticky top-0 hidden h-screen w-52 shrink-0 flex-col border-r border-line bg-bg0 md:flex">
        <div className="flex h-12 items-center gap-2 px-4">
          <Activity size={16} strokeWidth={2} className="text-live" />
          <span className="font-dense text-body font-semibold tracking-wide text-ink0">nz-monitor</span>
        </div>
        <nav className="flex flex-col gap-0.5 p-2">
          {domains.map((d) => (
            <NavLink
              key={d.key}
              to={d.to}
              className={`relative flex items-center gap-2.5 rounded px-2.5 py-2 font-dense text-label uppercase tracking-wide ${
                d.key === dom.key ? 'bg-bg2 text-ink0' : 'text-ink1 hover:bg-bg1 hover:text-ink0'
              }`}
            >
              <span className="relative">
                <d.icon size={16} strokeWidth={1.5} />
                {d.key === 'alertas' && <Badge count={alert.count} crit={alert.crit} />}
              </span>
              {d.label}
            </NavLink>
          ))}
          <div className="mt-1 px-2.5">
            <ThemeToggle />
          </div>
        </nav>

        {/* Usuario + rol + salir (AGENTS §12: siempre visible, no depende de "Ajustes") */}
        <div className="mt-auto border-t border-line p-3">
          <div className="min-w-0">
            <div className="truncate font-data text-body text-ink0">{user ?? '—'}</div>
            <div className="font-dense text-micro uppercase tracking-wide text-ink2">
              {role ? ROLE_LABEL[role] ?? role : ''}
            </div>
          </div>
          <div className="mt-2 flex items-center gap-1.5">
            <Link
              to="/ajustes"
              title="Cambiar contraseña"
              className="rounded border border-line p-1.5 text-ink1 hover:bg-bg2 hover:text-ink0"
            >
              <KeyRound size={14} strokeWidth={1.5} />
            </Link>
            <button
              onClick={logout}
              title="Salir"
              className="ml-auto flex items-center gap-1.5 rounded border border-line px-2.5 py-1.5 font-dense text-label uppercase tracking-wide text-ink1 hover:bg-bg2 hover:text-ink0"
            >
              <LogOut size={14} strokeWidth={1.5} />
              Salir
            </button>
          </div>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        {/* Header móvil */}
        <header className="sticky top-0 z-10 flex h-12 items-center gap-2 border-b border-line bg-bg0/95 px-4 backdrop-blur md:hidden">
          <Activity size={16} strokeWidth={2} className="text-live" />
          <span className="font-dense text-body font-semibold tracking-wide text-ink0">nz-monitor</span>
          <span className="ml-auto flex items-center gap-1">
            <Link
              to="/ajustes"
              title="Cambiar contraseña"
              className="rounded p-1.5 text-ink1 hover:bg-bg2 hover:text-ink0"
            >
              <KeyRound size={16} strokeWidth={1.5} />
            </Link>
            <ThemeToggle />
            <button onClick={logout} title="Salir" className="rounded p-1.5 text-ink1 hover:bg-bg2 hover:text-ink0">
              <LogOut size={16} strokeWidth={1.5} />
            </button>
          </span>
        </header>

        {/* Sub-tabs (nivel 2) */}
        {dom.subtabs.length > 0 && (
          <div className="sticky top-12 z-10 flex gap-1 overflow-x-auto border-b border-line bg-bg0/95 px-4 py-1.5 backdrop-blur md:top-0">
            {dom.subtabs.map((t) => (
              <NavLink
                key={t.to}
                to={t.to}
                className={({ isActive }) =>
                  `shrink-0 rounded px-2.5 py-1 font-dense text-label uppercase tracking-wide ${
                    isActive ? 'bg-bg2 text-ink0' : 'text-ink1 hover:text-ink0'
                  }`
                }
              >
                {t.label}
              </NavLink>
            ))}
          </div>
        )}

        <main className="mx-auto max-w-[1600px] px-4 py-5 pb-24 md:px-8 md:pb-8">
          <Outlet />
        </main>
      </div>

      {/* Bottom nav (móvil) — nivel 1. El número de ítems cambia según el rol (§12): rejilla dinámica. */}
      <nav
        className="fixed inset-x-0 bottom-0 z-20 grid border-t border-line bg-bg0/95 backdrop-blur md:hidden"
        style={{
          paddingBottom: 'env(safe-area-inset-bottom)',
          gridTemplateColumns: `repeat(${domains.length}, minmax(0, 1fr))`,
        }}
      >
        {domains.map((d) => {
          const active = d.key === dom.key
          return (
            <NavLink
              key={d.key}
              to={d.to}
              className={`flex flex-col items-center gap-0.5 py-2 ${active ? 'text-live' : 'text-ink2'}`}
            >
              <span className="relative">
                <d.icon size={20} strokeWidth={1.6} />
                {d.key === 'alertas' && <Badge count={alert.count} crit={alert.crit} />}
              </span>
              <span className="font-dense text-[10px] uppercase tracking-wide">{d.label}</span>
            </NavLink>
          )
        })}
      </nav>
    </div>
  )
}
