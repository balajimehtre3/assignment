import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import FloorDisplay    from './views/FloorDisplay.jsx'
import PlanningDesk    from './views/PlanningDesk.jsx'
import Management      from './views/Management.jsx'
import './App.css'

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <nav className="app-nav">
          <span className="app-logo">⚙ Atomberg MES</span>
          <div className="nav-links">
            <NavLink to="/floor"      className={({isActive}) => isActive ? 'active' : ''}>Floor Display</NavLink>
            <NavLink to="/planning"   className={({isActive}) => isActive ? 'active' : ''}>Planning Desk</NavLink>
            <NavLink to="/management" className={({isActive}) => isActive ? 'active' : ''}>Management</NavLink>
          </div>
        </nav>
        <main className="app-main">
          <Routes>
            <Route path="/"           element={<Navigate to="/floor" replace />} />
            <Route path="/floor"      element={<FloorDisplay />} />
            <Route path="/planning"   element={<PlanningDesk />} />
            <Route path="/management" element={<Management />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
