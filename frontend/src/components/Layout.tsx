import { Activity } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'

import { ThemeToggle } from './ThemeToggle'

const TABS = [
  { to: '/', label: 'Resumen', end: true },
  { to: '/tablas', label: 'Tablas', end: false },
]

export function Layout() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-line bg-bg0/95 backdrop-blur">
        <div className="mx-auto flex h-12 max-w-[1200px] items-center gap-4 px-4">
          <div className="flex items-center gap-2">
            <Activity size={16} strokeWidth={2} className="text-live" />
            <span className="font-dense text-body font-semibold tracking-wide text-ink0">
              nz-monitor
            </span>
          </div>
          <nav className="flex items-center gap-1">
            {TABS.map((t) => (
              <NavLink
                key={t.to}
                to={t.to}
                end={t.end}
                className={({ isActive }) =>
                  `rounded px-2.5 py-1 font-dense text-label uppercase tracking-wide ${
                    isActive ? 'bg-bg2 text-ink0' : 'text-ink1 hover:text-ink0'
                  }`
                }
              >
                {t.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
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
