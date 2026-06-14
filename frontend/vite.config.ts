import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// Dev: el front (5173) habla con el backend (8000) vía proxy → sin líos de CORS.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icon-192.png', 'icon-512.png'],
      manifest: {
        name: 'nz-monitor — observabilidad Netezza',
        short_name: 'nz-monitor',
        description: 'Skew, espacio y salud de Netezza',
        theme_color: '#0A0C10',
        background_color: '#0A0C10',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
    }),
  ],
  server: {
    host: true, // escucha en toda la red local (acceso desde el cel por la IP de la PC)
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
  // `vite preview` sirve el build (con service worker → PWA instalable). allowedHosts:true
  // acepta el host del túnel HTTPS (trycloudflare/ngrok). Proxy de /api al backend.
  preview: {
    host: true,
    port: 4173,
    allowedHosts: true,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
})
