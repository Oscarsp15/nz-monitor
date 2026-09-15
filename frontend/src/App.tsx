import { lazy, type ReactNode } from 'react'
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'

import { Layout } from './components/Layout'
import { useAuth } from './lib/auth'
import { Overview } from './pages/Overview'

// Carga por ruta (AGENTS §8/§9): todo lo que no sea la pantalla de aterrizaje se parte en su
// propio chunk. Empieza por las pantallas solo-admin (Users, Settings), que la mayoría de
// usuarios (viewer/operador) nunca llegan a pedir. `Layout` envuelve el `Outlet` en un
// `Suspense` con un fallback coherente con el resto (`PageSkeleton`).
const Tables = lazy(() => import('./pages/Tables').then((m) => ({ default: m.Tables })))
const Dataslices = lazy(() => import('./pages/Dataslices').then((m) => ({ default: m.Dataslices })))
const DataslicePage = lazy(() =>
  import('./pages/DataslicePage').then((m) => ({ default: m.DataslicePage })),
)
const Owners = lazy(() => import('./pages/Owners').then((m) => ({ default: m.Owners })))
const SftpDisk = lazy(() => import('./pages/SftpDisk').then((m) => ({ default: m.SftpDisk })))
const SftpOldFiles = lazy(() =>
  import('./pages/SftpOldFiles').then((m) => ({ default: m.SftpOldFiles })),
)
const Alerts = lazy(() => import('./pages/Alerts').then((m) => ({ default: m.Alerts })))
const TableDetail = lazy(() =>
  import('./pages/TableDetail').then((m) => ({ default: m.TableDetail })),
)
const Settings = lazy(() => import('./pages/Settings').then((m) => ({ default: m.Settings })))
const Users = lazy(() => import('./pages/Users').then((m) => ({ default: m.Users })))

/** La UI no debe depender solo de ocultar el enlace: si un no-admin entra por URL, va al inicio. */
function AdminOnly({ children }: { children: ReactNode }) {
  const { isAdmin } = useAuth()
  return isAdmin ? <>{children}</> : <Navigate to="/" replace />
}

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Overview /> },
      { path: 'tablas', element: <Tables /> },
      { path: 'dataslices', element: <Dataslices /> },
      { path: 'dataslice/:id', element: <DataslicePage /> },
      { path: 'owners', element: <Owners /> },
      { path: 'sftp', element: <Navigate to="/sftp/disco" replace /> },
      { path: 'sftp/disco', element: <SftpDisk /> },
      { path: 'sftp/archivos', element: <SftpOldFiles /> },
      { path: 'alertas', element: <Alerts /> },
      { path: 'tabla/:objid', element: <TableDetail /> },
      { path: 'ajustes', element: <Settings /> },
      {
        path: 'usuarios',
        element: (
          <AdminOnly>
            <Users />
          </AdminOnly>
        ),
      },
    ],
  },
])

export function App() {
  return <RouterProvider router={router} />
}
