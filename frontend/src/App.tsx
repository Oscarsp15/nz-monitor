import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'

import { Layout } from './components/Layout'
import { Alerts } from './pages/Alerts'
import { DataslicePage } from './pages/DataslicePage'
import { Dataslices } from './pages/Dataslices'
import { Overview } from './pages/Overview'
import { Owners } from './pages/Owners'
import { Settings } from './pages/Settings'
import { SftpPlaceholder } from './pages/SftpPlaceholder'
import { TableDetail } from './pages/TableDetail'
import { Tables } from './pages/Tables'

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
      { path: 'sftp/disco', element: <SftpPlaceholder /> },
      { path: 'sftp/archivos', element: <SftpPlaceholder /> },
      { path: 'alertas', element: <Alerts /> },
      { path: 'tabla/:objid', element: <TableDetail /> },
      { path: 'ajustes', element: <Settings /> },
    ],
  },
])

export function App() {
  return <RouterProvider router={router} />
}
