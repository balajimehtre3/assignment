/**
 * api.js – Typed fetch wrappers for every backend endpoint.
 *
 * Auth flow:
 *  - Reads the access token from localStorage on every call.
 *  - On 401, attempts one silent token refresh then retries the original request.
 *  - If the refresh also fails, dispatches a custom 'auth:logout' event so
 *    AuthContext can clear state and redirect to login without a circular import.
 */

const BASE = '/api'

// ── Core fetch wrapper ────────────────────────────────────────────────────────

async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) return null

  const res = await fetch(`${BASE}/auth/refresh`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ refresh_token: refreshToken }),
  })
  if (!res.ok) return null

  const data = await res.json()
  localStorage.setItem('access_token', data.access_token)
  return data.access_token
}

async function request(method, path, body, retry = true) {
  const token = localStorage.getItem('access_token')

  const opts = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  }
  if (body !== undefined) opts.body = JSON.stringify(body)

  const res = await fetch(BASE + path, opts)

  // Silent refresh + retry on 401
  if (res.status === 401 && retry) {
    const newToken = await refreshAccessToken()
    if (newToken) {
      return request(method, path, body, false) // retry once with new token
    }
    // Refresh failed — force logout
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    window.dispatchEvent(new CustomEvent('auth:logout'))
    throw new Error('Session expired. Please log in again.')
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const d = await res.json()
      detail = d.detail || JSON.stringify(d)
    } catch {}
    throw new Error(detail)
  }

  if (res.status === 204) return null
  return res.json()
}

const get   = (path)       => request('GET',    path)
const post  = (path, body) => request('POST',   path, body)
const patch = (path, body) => request('PATCH',  path, body)
const del   = (path)       => request('DELETE', path)

// ── Auth ──────────────────────────────────────────────────────────────────────
export const getMe = () => get('/auth/me')

// ── Machines ──────────────────────────────────────────────────────────────────
export const getMachines = ()   => get('/machines')
export const getMachine  = (mc) => get(`/machines/${mc}`)

// ── SKUs ──────────────────────────────────────────────────────────────────────
export const getSkus = () => get('/skus')

// ── Downtime reasons ──────────────────────────────────────────────────────────
export const getDowntimeReasons = () => get('/downtime-reasons')

// ── Orders ────────────────────────────────────────────────────────────────────
export function getOrders(params = {}) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, v) })
  return get(`/orders?${q}`)
}
export const getOrder    = (no)       => get(`/orders/${no}`)
export const createOrder = (body)     => post('/orders', body)
export const updateOrder = (no, body) => patch(`/orders/${no}`, body)
export const deleteOrder = (no)       => del(`/orders/${no}`)

// ── Unit events ───────────────────────────────────────────────────────────────
export function getUnitEvents(params = {}) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, v) })
  return get(`/unit-events?${q}`)
}

// ── Downtime events ───────────────────────────────────────────────────────────
export function getDowntimeEvents(params = {}) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, v) })
  return get(`/downtime-events?${q}`)
}

// ── Floor snapshot ────────────────────────────────────────────────────────────
export const getFloorSnapshot = () => get('/floor/snapshot')

// ── Analytics ─────────────────────────────────────────────────────────────────
export const getAnalyticsSummary = (from, to) =>
  get(`/analytics/summary?from_date=${from}&to_date=${to}`)
export const getOEE = (from, to) =>
  get(`/analytics/oee?from_date=${from}&to_date=${to}`)
