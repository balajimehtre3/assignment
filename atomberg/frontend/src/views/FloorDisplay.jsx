import { useState, useEffect, useCallback } from 'react'
import { getFloorSnapshot } from '../api.js'
import './FloorDisplay.css'

const REFRESH_MS = 30_000 // 30 s auto-refresh

function statusClass(s) {
  if (!s) return 'status-idle'
  const m = s.toLowerCase()
  if (m === 'in_progress') return 'status-running'
  if (m === 'on_hold' || m === 'planned') return 'status-hold'
  if (m === 'completed') return 'status-done'
  return 'status-idle'
}

function priorityDot(p) {
  if (p === 'high')   return <span className="dot dot-red"   title="High priority" />
  if (p === 'normal') return <span className="dot dot-yellow" title="Normal priority" />
  return                      <span className="dot dot-gray"  title="Low priority" />
}

function MachineCard({ data, simNow }) {
  const { machine, current_order, units_today, active_downtime, availability_pct, dt_minutes_today } = data
  const isDown = !!active_downtime
  const hasOrder = !!current_order

  const pct = hasOrder
    ? Math.min(100, Math.round((current_order.qty_completed / current_order.qty_planned) * 100))
    : null

  return (
    <div className={`machine-card ${isDown ? 'machine-down' : hasOrder ? 'machine-running' : 'machine-idle'}`}>
      {/* header */}
      <div className="mc-header">
        <span className="mc-code">{machine.machine_code}</span>
        <span className="mc-name">{machine.name}</span>
        <span className={`mc-state-badge ${isDown ? 'badge-red' : hasOrder ? 'badge-green' : 'badge-gray'}`}>
          {isDown ? '⚠ STOPPED' : hasOrder ? '▶ RUNNING' : '— IDLE'}
        </span>
      </div>

      {/* downtime banner */}
      {isDown && (
        <div className="mc-downtime-banner">
          <span className="dt-icon">⛔</span>
          <div>
            <div className="dt-reason">{active_downtime.reason_description}</div>
            <div className="dt-meta">
              {active_downtime.category.toUpperCase()} · since {active_downtime.started_at.slice(11, 16)}
              {active_downtime.note ? ` · ${active_downtime.note}` : ''}
            </div>
          </div>
        </div>
      )}

      {/* current order */}
      {hasOrder ? (
        <div className="mc-order">
          <div className="mc-order-top">
            <span className="order-no">{current_order.order_no}</span>
            {priorityDot(current_order.priority)}
          </div>
          <div className="sku-desc">{current_order.sku_description}</div>

          <div className="progress-row">
            <div className="progress-bar-wrap">
              <div className="progress-bar" style={{ width: `${pct}%` }} />
            </div>
            <span className="progress-pct">{pct}%</span>
          </div>

          <div className="order-counts">
            <span className="count-done">{current_order.qty_completed.toLocaleString()}</span>
            <span className="count-sep"> / </span>
            <span className="count-total">{current_order.qty_planned.toLocaleString()} units</span>
          </div>
        </div>
      ) : (
        <div className="mc-no-order">No active order</div>
      )}

      {/* stats row */}
      <div className="mc-stats">
        <div className="stat">
          <div className="stat-val">{units_today.toLocaleString()}</div>
          <div className="stat-lbl">Units today</div>
        </div>
        <div className="stat">
          <div className={`stat-val ${availability_pct < 70 ? 'val-red' : availability_pct < 85 ? 'val-yellow' : 'val-green'}`}>
            {availability_pct}%
          </div>
          <div className="stat-lbl">Availability</div>
        </div>
        <div className="stat">
          <div className="stat-val">{Math.round(dt_minutes_today)} min</div>
          <div className="stat-lbl">Downtime today</div>
        </div>
        <div className="stat">
          <div className="stat-val">{machine.target_units_per_hour}</div>
          <div className="stat-lbl">Target / hr</div>
        </div>
      </div>
    </div>
  )
}

export default function FloorDisplay() {
  const [snapshot, setSnapshot] = useState([])
  const [lastUpdated, setLastUpdated] = useState(null)
  const [error, setError]   = useState(null)
  const [ticks, setTicks]   = useState(0)

  const load = useCallback(async () => {
    try {
      const data = await getFloorSnapshot()
      setSnapshot(data)
      setLastUpdated(new Date())
      setError(null)
    } catch (e) {
      setError(e.message)
    }
  }, [])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    const id = setInterval(() => { load(); setTicks(t => t + 1) }, REFRESH_MS)
    return () => clearInterval(id)
  }, [load])

  // countdown timer
  const [countdown, setCountdown] = useState(REFRESH_MS / 1000)
  useEffect(() => {
    setCountdown(REFRESH_MS / 1000)
    const id = setInterval(() => setCountdown(c => Math.max(0, c - 1)), 1000)
    return () => clearInterval(id)
  }, [ticks, lastUpdated])

  const simNow = '2026-08-17 09:15'

  return (
    <div className="floor-wrap">
      <div className="floor-header">
        <div>
          <h1 className="floor-title">Factory Floor</h1>
          <div className="floor-subtitle">Simulated time: {simNow}</div>
        </div>
        <div className="floor-meta">
          {error
            ? <span className="floor-error">⚠ {error}</span>
            : lastUpdated && <span className="floor-updated">Updated {lastUpdated.toLocaleTimeString()}</span>
          }
          <span className="floor-refresh">Refreshing in {countdown}s</span>
        </div>
      </div>

      {snapshot.length === 0 && !error && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
          <div className="spinner" />
        </div>
      )}

      <div className="floor-grid">
        {snapshot.map(d => (
          <MachineCard key={d.machine.machine_code} data={d} simNow={simNow} />
        ))}
      </div>
    </div>
  )
}
