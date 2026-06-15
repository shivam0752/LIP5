import { NavLink, Outlet, useLocation } from 'react-router-dom'
import './index.css'

const NAV = [
  { to: '/',        icon: '⚡', label: 'Dashboard' },
  { to: '/history', icon: '📋', label: 'History'   },
  { to: '/logs',    icon: '🖥', label: 'Logs'      },
]

export default function App() {
  return (
    <div className="app-shell">
      {/* Sidebar */}
      <nav className="sidebar" aria-label="Main navigation">
        <div className="sidebar-logo">
          <h1>LIP5</h1>
          <p>App Store Pulse · Groww</p>
        </div>

        {NAV.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <span className="nav-icon" aria-hidden="true">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Content */}
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
