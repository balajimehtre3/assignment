/**
 * AuthContext.jsx
 * Global auth state: tokens, user info, login, logout, token refresh.
 * Stored in localStorage so sessions survive page reloads.
 */

import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'

const BASE = '/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]           = useState(null)   // { username, role }
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem('access_token') || null)
  const [loading, setLoading]     = useState(true)   // true while verifying stored token
  const refreshTimer = useRef(null)

  // ── helpers ────────────────────────────────────────────────────────────────

  function saveTokens(access, refresh) {
    localStorage.setItem('access_token',  access)
    localStorage.setItem('refresh_token', refresh)
    setAccessToken(access)
  }

  function clearTokens() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setAccessToken(null)
    setUser(null)
    if (refreshTimer.current) clearTimeout(refreshTimer.current)
  }

  // Decode the JWT payload (no verification — server validates on every request)
  function decodePayload(token) {
    try {
      return JSON.parse(atob(token.split('.')[1]))
    } catch {
      return null
    }
  }

  // Schedule a silent refresh 60 s before the access token expires
  const scheduleRefresh = useCallback((token) => {
    if (refreshTimer.current) clearTimeout(refreshTimer.current)
    const payload = decodePayload(token)
    if (!payload?.exp) return
    const msUntilExpiry = payload.exp * 1000 - Date.now()
    const refreshIn     = Math.max(msUntilExpiry - 60_000, 5_000)
    refreshTimer.current = setTimeout(silentRefresh, refreshIn)
  }, []) // eslint-disable-line

  // ── silent refresh ─────────────────────────────────────────────────────────

  const silentRefresh = useCallback(async () => {
    const storedRefresh = localStorage.getItem('refresh_token')
    if (!storedRefresh) { clearTokens(); return }
    try {
      const res = await fetch(`${BASE}/auth/refresh`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ refresh_token: storedRefresh }),
      })
      if (!res.ok) throw new Error('refresh failed')
      const data = await res.json()
      localStorage.setItem('access_token', data.access_token)
      setAccessToken(data.access_token)
      scheduleRefresh(data.access_token)
    } catch {
      clearTokens()
    }
  }, [scheduleRefresh])

  // ── verify stored token on mount ──────────────────────────────────────────

  useEffect(() => {
    async function verify() {
      const token = localStorage.getItem('access_token')
      if (!token) { setLoading(false); return }

      try {
        const res = await fetch(`${BASE}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!res.ok) throw new Error()
        const data = await res.json()
        setUser({ username: data.username, role: data.role, email: data.email })
        scheduleRefresh(token)
      } catch {
        clearTokens()
      } finally {
        setLoading(false)
      }
    }
    verify()
  }, [scheduleRefresh])

  // ── public API ─────────────────────────────────────────────────────────────

  async function login(username, password) {
    const res = await fetch(`${BASE}/auth/login`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ username, password }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Login failed')
    }
    const data = await res.json()
    saveTokens(data.access_token, data.refresh_token)
    setUser({ username: data.username, role: data.role })
    scheduleRefresh(data.access_token)
  }

  function logout() {
    clearTokens()
  }

  return (
    <AuthContext.Provider value={{ user, accessToken, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
