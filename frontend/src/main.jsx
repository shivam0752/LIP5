import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'

import App from './App.jsx'
import Dashboard from './pages/Dashboard.jsx'
import History from './pages/History.jsx'
import Logs from './pages/Logs.jsx'
import './index.css'

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true,      element: <Dashboard /> },
      { path: 'history',  element: <History /> },
      { path: 'logs',     element: <Logs /> },
    ],
  },
])

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
