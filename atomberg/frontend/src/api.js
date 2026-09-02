const BASE = '/api'

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (body !== undefined) opts.body = JSON.stringify(body)
  const res = await fetch(BASE + path, opts)
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try { const d = await res.json(); detail = d.detail || JSON.stringify(d) } catch {}
    throw new Error(detail)
  }
  if (res.status === 204) return null
  return res.json()
}

const get  = (path)        => request('GET',    path)
const post = (path, body)  => request('POST',   path, body)
const patch= (path, body)  => request('PATCH',  path, body)
const del  = (path)        => request('DELETE', path)

// ── Machines ──────────────────────────────────────────────
export const getMachines = ()   => get('/machines')
export const getMachine  = (mc) => get(`/machines/${mc}`)

// ── SKUs ──────────────────────────────────────────────────
export const getSkus = () => get('/skus')

// ── Downtime reasons ──────────────────────────────────────
export const getDowntimeReasons = () => get('/downtime-reasons')

// ── Orders ────────────────────────────────────────────────
export function getOrders(params = {}) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, v) })
  return get(`/orders?${q}`)
}
export const getOrder    = (no)        => get(`/orders/${no}`)
export const createOrder = (body)      => post('/orders', body)
export const updateOrder = (no, body)  => patch(`/orders/${no}`, body)
export const deleteOrder = (no)        => del(`/orders/${no}`)

// ── Unit events ───────────────────────────────────────────
export function getUnitEvents(params = {}) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, v) })
  return get(`/unit-events?${q}`)
}

// ── Downtime events ───────────────────────────────────────
export function getDowntimeEvents(params = {}) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, v) })
  return get(`/downtime-events?${q}`)
}

// ── Floor snapshot ────────────────────────────────────────
export const getFloorSnapshot = () => get('/floor/snapshot')

// ── Analytics ─────────────────────────────────────────────
export const getAnalyticsSummary = (from, to) => get(`/analytics/summary?from_date=${from}&to_date=${to}`)
export const getOEE              = (from, to) => get(`/analytics/oee?from_date=${from}&to_date=${to}`)
