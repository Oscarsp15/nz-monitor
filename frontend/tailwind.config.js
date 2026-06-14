/** @type {import('tailwindcss').Config} */
// Tokens del DESIGN.md mapeados a variables CSS (ver src/index.css) para soportar tema claro/oscuro.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg0: 'var(--bg-0)',
        bg1: 'var(--bg-1)',
        bg2: 'var(--bg-2)',
        line: 'var(--line)',
        'line-strong': 'var(--line-strong)',
        ink0: 'var(--ink-0)',
        ink1: 'var(--ink-1)',
        ink2: 'var(--ink-2)',
        ok: 'var(--ok)',
        warn: 'var(--warn)',
        crit: 'var(--crit)',
        info: 'var(--info)',
        live: 'var(--live)',
      },
      fontFamily: {
        data: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
        ui: ['"IBM Plex Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        dense: ['"IBM Plex Sans Condensed"', '"IBM Plex Sans"', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '6px',
        pill: '999px',
      },
      fontSize: {
        micro: '0.6875rem',
        label: '0.75rem',
        body: '0.8125rem',
        kpi: '1.75rem',
        'kpi-lg': '2.25rem',
      },
    },
  },
  plugins: [],
}
