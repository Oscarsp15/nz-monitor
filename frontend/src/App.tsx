import { createBrowserRouter, RouterProvider } from 'react-router-dom'

import { Layout } from './components/Layout'
import { Alerts } from './pages/Alerts'
import { Dataslices } from './pages/Dataslices'
import { Overview } from './pages/Overview'
import { Owners } from './pages/Owners'
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
      { path: 'owners', element: <Owners /> },
      { path: 'alertas', element: <Alerts /> },
      { path: 'tabla/:objid', element: <TableDetail /> },
    ],
  },
])

export function App() {
  return <RouterProvider router={router} />
}
