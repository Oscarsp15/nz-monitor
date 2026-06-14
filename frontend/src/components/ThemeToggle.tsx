import { Moon, Sun } from 'lucide-react'

import { useTheme } from '../theme'

export function ThemeToggle() {
  const { theme, toggle } = useTheme()
  return (
    <button
      onClick={toggle}
      className="rounded p-1.5 text-ink1 hover:bg-bg2 hover:text-ink0"
      title={theme === 'dark' ? 'Tema claro' : 'Tema oscuro'}
      aria-label="Cambiar tema"
    >
      {theme === 'dark' ? <Sun size={16} strokeWidth={1.5} /> : <Moon size={16} strokeWidth={1.5} />}
    </button>
  )
}
