import { createBrowserRouter, RouterProvider } from 'react-router-dom'

import { Layout } from './components/Layout'
import { Overview } from './pages/Overview'
import { TableDetail } from './pages/TableDetail'
import { Tables } from './pages/Tables'

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Overview /> },
      { path: 'tablas', element: <Tables /> },
      { path: 'tabla/:objid', element: <TableDetail /> },
    ],
  },
])

export function App() {
  return <RouterProvider router={router} />
}
