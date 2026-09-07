import { useEffect }                                          from 'react'
import { BrowserRouter, Navigate, NavLink, Route, Routes }   from 'react-router-dom'
import { AuthProvider, useAuth }                              from './AuthContext.jsx'
import Login          from './views/Login.jsx'
import FloorDisplay   from './views/FloorDisplay.jsx'
import PlanningDesk   from './views/PlanningDesk.jsx'
import Management     from './views/Management.jsx'
import './App.css'

// ── Role badge colours ────────────────────────────────────────────────────────
const ROLE_BADGE = {
  admin:      'badge-red',
  planner:    'badge-blue',
  supervisor: 'badge-green',
  manager:    'badge-accent',
  viewer:     'badge-gray',
}

// ── Protected shell ───────────────────────────────────────────────────────────
function AppShell() {
  const { user, logout } = useAuth()

  // Listen for the forced-logout event dispatched by api.js on 401
  useEffect(() => {
    const handler = () => logout()
    window.addEventListener('auth:logout', handler)
    return () => window.removeEventListener('auth:logout', handler)
  }, [logout])

  return (
    <div className="app-shell">
      <nav className="app-nav">
        <span className="app-logo">⚙ Atomberg MES</span>

        <div className="nav-links">
          <NavLink to="/floor"      className={({ isActive }) => isActive ? 'active' : ''}>
            Floor Display
          </NavLink>
          <NavLink to="/planning"   className={({ isActive }) => isActive ? 'active' : ''}>
            Planning Desk
          </NavLink>
          <NavLink to="/management" className={({ isActive }) => isActive ? 'active' : ''}>
            Management
          </NavLink>
        </div>

        {/* User info + logout */}
        <div className="nav-user">
          <span className={`badge ${ROLE_BADGE[user?.role] || 'badge-gray'}`}>
            {user?.role}
          </span>
          <span className="nav-username">{user?.username}</span>
          <button className="btn-ghost nav-logout" onClick={logout} title="Sign out">
            ⎋ Sign out
          </button>
        </div>
      </nav>

      <main className="app-main">
        <Routes>
          <Route path="/"           element={<Navigate to="/floor" replace />} />
          <Route path="/floor"      element={<FloorDisplay />} />
          <Route path="/planning"   element={<PlanningDesk />} />
          <Route path="/management" element={<Management />} />
          <Route path="*"           element={<Navigate to="/floor" replace />} />
        </Routes>
      </main>
    </div>
  )
}

// ── Root: gate on auth state ──────────────────────────────────────────────────
function Root() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex',
        alignItems: 'center', justifyContent: 'center',
      }}>
        <div className="spinner" style={{ width: 32, height: 32 }} />
      </div>
    )
  }

  return user ? <AppShell /> : <Login />
}

// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Root />
      </BrowserRouter>
    </AuthProvider>
  )
}
