import { useState } from 'react'
import { useAuth } from '../AuthContext.jsx'
import './Login.css'

export default function Login() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error,    setError]    = useState(null)
  const [loading,  setLoading]  = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(username, password)
      // AuthContext sets user → App re-renders to protected shell
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        {/* Logo / brand */}
        <div className="login-brand">
          <span className="login-logo">⚙</span>
          <h1 className="login-title">Atomberg MES</h1>
          <p className="login-sub">Manufacturing Execution System</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {error && (
            <div className="login-error" role="alert">
              {error}
            </div>
          )}

          <label className="login-field">
            <span>Username</span>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
              required
              placeholder="Enter username"
            />
          </label>

          <label className="login-field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              placeholder="Enter password"
            />
          </label>

          <button
            type="submit"
            className="btn-primary login-btn"
            disabled={loading || !username || !password}
          >
            {loading ? <span className="spinner" style={{width:16,height:16}} /> : 'Sign in'}
          </button>
        </form>

        <div className="login-hint">
          <p>Default accounts</p>
          <div className="login-accounts">
            <span><b>admin</b> / admin123</span>
            <span><b>planner</b> / planner123</span>
            <span><b>supervisor</b> / supervisor123</span>
            <span><b>manager</b> / manager123</span>
          </div>
        </div>
      </div>
    </div>
  )
}
