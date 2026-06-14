import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

type Theme = 'dark' | 'light'
const KEY = 'nzm-theme'

interface ThemeCtx {
  theme: Theme
  toggle: () => void
}
const Ctx = createContext<ThemeCtx | null>(null)

function initial(): Theme {
  const saved = localStorage.getItem(KEY)
  if (saved === 'dark' || saved === 'light') return saved
  // respeta el tema del sistema si no hay elección guardada
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(initial)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem(KEY, theme)
    const color = theme === 'dark' ? '#0A0C10' : '#F4F6F8'
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', color)
  }, [theme])

  const toggle = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))
  return <Ctx.Provider value={{ theme, toggle }}>{children}</Ctx.Provider>
}

export function useTheme(): ThemeCtx {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useTheme fuera de ThemeProvider')
  return ctx
}
