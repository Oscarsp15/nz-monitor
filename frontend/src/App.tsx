import { type ReactNode } from 'react'
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'

import { Layout } from './components/Layout'
import { useAuth } from './lib/auth'
import { Alerts } from './pages/Alerts'
import { DataslicePage } from './pages/DataslicePage'
import { Dataslices } from './pages/Dataslices'
import { Overview } from './pages/Overview'
import { Owners } from './pages/Owners'
import { Settings } from './pages/Settings'
import { SftpDisk } from './pages/SftpDisk'
import { SftpOldFiles } from './pages/SftpOldFiles'
import { TableDetail } from './pages/TableDetail'
import { Tables } from './pages/Tables'
import { Users } from './pages/Users'

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
