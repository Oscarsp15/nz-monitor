import { useQuery } from '@tanstack/react-query'
import { Activity, Bell, Settings as SettingsIcon } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'

import { api } from '../lib/api'
import { ThemeToggle } from './ThemeToggle'

const TABS = [
  { to: '/', label: 'Resumen', end: true },
  { to: '/tablas', label: 'Tablas', end: false },
  { to: '/dataslices', label: 'Dataslices', end: false },
  { to: '/owners', label: 'Owners', end: false },
  { to: '/alertas', label: 'Alertas', end: false },
]

function AlertBell() {
  const q = useQuery({ queryKey: ['mon', 'alerts'], queryFn: api.monitoringAlerts })
  const count = q.data?.data?.alerts?.length ?? 0
  const crit = (q.data?.data?.alerts ?? []).some((a) => a.level === 'crit')
  return (
    <NavLink to="/alertas" className="relative rounded p-1.5 text-ink1 hover:bg-bg2 hover:text-ink0" title="Alertas">
      <Bell size={16} strokeWidth={1.5} />
      {count > 0 && (
        <span
          className="absolute -right-0.5 -top-0.5 flex h-3.5 min-w-3.5 items-center justify-center rounded-pill px-1 font-data text-[9px] text-bg0"
          style={{ background: crit ? 'var(--crit)' : 'var(--warn)' }}
        >
          {count}
        </span>
      )}
    </NavLink>
  )
}

export function Layout() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-line bg-bg0/95 backdrop-blur">
        <div className="mx-auto flex h-12 max-w-[1200px] items-center gap-3 px-4">
          <div className="flex shrink-0 items-center gap-2">
            <Activity size={16} strokeWidth={2} className="text-live" />
            <span className="font-dense text-body font-semibold tracking-wide text-ink0">
              nz-monitor
            </span>
          </div>
          <nav className="flex items-center gap-1 overflow-x-auto">
            {TABS.map((t) => (
              <NavLink
                key={t.to}
                to={t.to}
                end={t.end}
                className={({ isActive }) =>
                  `shrink-0 rounded px-2.5 py-1 font-dense text-label uppercase tracking-wide ${
                    isActive ? 'bg-bg2 text-ink0' : 'text-ink1 hover:text-ink0'
                  }`
                }
              >
                {t.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex shrink-0 items-center gap-1">
            <AlertBell />
            <NavLink
              to="/ajustes"
              className="rounded p-1.5 text-ink1 hover:bg-bg2 hover:text-ink0"
              title="Ajustes"
            >
              <SettingsIcon size={16} strokeWidth={1.5} />
            </NavLink>
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1200px] px-4 py-5">
        <Outlet />
      </main>
    </div>
  )
}
