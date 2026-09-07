import { useState, useEffect } from 'react'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, Cell, PieChart, Pie,
} from 'recharts'
import { getAnalyticsSummary, getOEE } from '../api.js'
import './Management.css'

// ── colour palette ────────────────────────────────────────────────────────────
const MC_COLORS = { 'MC-01': '#4aad7a', 'MC-02': '#4a8ae0', 'MC-03': '#e0a94a', 'MC-04': '#c06abb' }
const MC_LIST   = ['MC-01', 'MC-02', 'MC-03', 'MC-04']

// ── small components ──────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, color }) {
  return (
    <div className="kpi-card card">
      <div className="kpi-val" style={color ? { color } : {}}>{value}</div>
      <div className="kpi-label">{label}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  )
}

function SectionTitle({ children }) {
  return <h2 className="section-title">{children}</h2>
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tip">
      <div className="chart-tip-label">{label}</div>
      {payload.map(p => (
        <div key={p.dataKey} style={{ color: p.color, fontSize: 12 }}>
          {p.name}: <strong>{typeof p.value === 'number' ? p.value.toLocaleString() : p.value}</strong>
        </div>
      ))}
    </div>
  )
}

// ── main ──────────────────────────────────────────────────────────────────────

export default function Management() {
  const [fromDate, setFromDate] = useState('2026-08-03')
  const [toDate,   setToDate]   = useState('2026-08-17')
  const [summary,  setSummary]  = useState(null)
  const [oee,      setOee]      = useState(null)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState(null)

  async function load() {
    setLoading(true); setError(null)
    try {
      const [s, o] = await Promise.all([
        getAnalyticsSummary(fromDate, toDate),
        getOEE(fromDate, toDate),
      ])
      setSummary(s)
      setOee(o)
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, []) // eslint-disable-line

  // ── derived data ──────────────────────────────────────────────────────────

  // daily output pivot: [{day, 'MC-01': n, 'MC-02': n, ...}]
  const dailyChart = (() => {
    if (!summary) return []
    const map = {}
    summary.daily_output.forEach(({ day, machine_code, units }) => {
      if (!map[day]) map[day] = { day }
      map[day][machine_code] = units
    })
    return Object.values(map).sort((a, b) => a.day.localeCompare(b.day))
  })()

  // downtime by machine stacked: [{machine_code, planned, unplanned}]
  const downtimeChart = (() => {
    if (!summary) return []
    const map = {}
    summary.downtime.forEach(({ machine_code, category, minutes }) => {
      if (!map[machine_code]) map[machine_code] = { machine_code, planned: 0, unplanned: 0 }
      map[machine_code][category] = minutes
    })
    return MC_LIST.map(mc => map[mc] || { machine_code: mc, planned: 0, unplanned: 0 })
  })()

  // order status pie
  const orderPie = (() => {
    if (!summary) return []
    const colors = {
      completed: '#4aad7a', in_progress: '#4a8ae0', planned: '#8b9793',
      released: '#e0a94a', on_hold: '#e0c84a', cancelled: '#e05a4a',
    }
    return summary.order_summary.map(({ status, count }) => ({
      name: status.replace('_', ' '), value: count, color: colors[status] || '#8b9793',
    }))
  })()

  // totals
  const totalUnits    = summary?.performance.reduce((s, r) => s + r.units_produced, 0) ?? 0
  const totalTarget   = summary?.performance.reduce((s, r) => s + r.target, 0) ?? 0
  const avgOee        = oee ? Math.round(oee.reduce((s, r) => s + r.oee, 0) / oee.length) : 0
  const totalDtPlanned   = downtimeChart.reduce((s, r) => s + r.planned, 0)
  const totalDtUnplanned = downtimeChart.reduce((s, r) => s + r.unplanned, 0)

  return (
    <div className="mgmt-wrap">
      {/* ── controls ── */}
      <div className="mgmt-header">
        <div>
          <h1 className="page-title">Management Dashboard</h1>
          <div className="page-sub">Factory performance overview</div>
        </div>
        <div className="date-controls">
          <label>
            <span>From</span>
            <input type="date" value={fromDate} onChange={e => setFromDate(e.target.value)} />
          </label>
          <label>
            <span>To</span>
            <input type="date" value={toDate} onChange={e => setToDate(e.target.value)} />
          </label>
          <button className="btn-primary" onClick={load} disabled={loading}>
            {loading ? 'Loading…' : 'Apply'}
          </button>
        </div>
      </div>

      {error && <div className="mgmt-error">{error}</div>}

      {loading && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
          <div className="spinner" />
        </div>
      )}

      {!loading && summary && oee && (
        <>
          {/* ── KPI row ── */}
          <div className="kpi-row">
            <KpiCard label="Total Units Produced" value={totalUnits.toLocaleString()}
              sub={`Target: ${totalTarget.toLocaleString()}`} color="var(--green)" />
            <KpiCard label="Achievement"
              value={`${totalTarget ? Math.round(totalUnits / totalTarget * 100) : 0}%`}
              sub={`${summary.period.days} day period`} />
            <KpiCard label="Avg OEE" value={`${avgOee}%`}
              sub="Across all machines"
              color={avgOee >= 80 ? 'var(--green)' : avgOee >= 60 ? 'var(--yellow)' : 'var(--red)'} />
            <KpiCard label="Planned Downtime" value={`${Math.round(totalDtPlanned)} min`}
              sub={`${Math.round(totalDtPlanned / 60 * 10) / 10} hrs`} />
            <KpiCard label="Unplanned Downtime" value={`${Math.round(totalDtUnplanned)} min`}
              sub={`${Math.round(totalDtUnplanned / 60 * 10) / 10} hrs`}
              color={totalDtUnplanned > 200 ? 'var(--red)' : 'var(--ink)'} />
          </div>

          {/* ── Output vs Target table ── */}
          <SectionTitle>Output vs Target — by Machine</SectionTitle>
          <div className="card table-card">
            <table>
              <thead>
                <tr>
                  <th>Machine</th>
                  <th style={{textAlign:'right'}}>Units Produced</th>
                  <th style={{textAlign:'right'}}>Target</th>
                  <th style={{textAlign:'right'}}>Achievement</th>
                  <th>Performance bar</th>
                </tr>
              </thead>
              <tbody>
                {summary.performance.map(r => {
                  const pct = r.achievement_pct
                  const color = pct >= 90 ? 'var(--green)' : pct >= 70 ? 'var(--yellow)' : 'var(--red)'
                  return (
                    <tr key={r.machine_code}>
                      <td><span style={{fontFamily:'var(--font-mono)',fontWeight:600}}>{r.machine_code}</span></td>
                      <td style={{textAlign:'right',fontFamily:'var(--font-mono)'}}>{r.units_produced.toLocaleString()}</td>
                      <td style={{textAlign:'right',fontFamily:'var(--font-mono)',color:'var(--muted)'}}>{r.target.toLocaleString()}</td>
                      <td style={{textAlign:'right',fontFamily:'var(--font-mono)',color,fontWeight:700}}>{pct}%</td>
                      <td>
                        <div style={{width:'100%',height:6,background:'var(--surface3)',borderRadius:99,overflow:'hidden'}}>
                          <div style={{width:`${Math.min(100,pct)}%`,height:'100%',background:color,borderRadius:99}} />
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* ── Daily output chart ── */}
          <SectionTitle>Daily Output by Machine</SectionTitle>
          <div className="card chart-card">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={dailyChart} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: 'var(--muted)' }}
                  tickFormatter={d => d.slice(5)} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--muted)' }} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: 12, color: 'var(--ink2)' }} />
                {MC_LIST.map(mc => (
                  <Bar key={mc} dataKey={mc} stackId="a" fill={MC_COLORS[mc]} name={mc} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* ── OEE table ── */}
          <SectionTitle>OEE by Machine</SectionTitle>
          <div className="card table-card">
            <table>
              <thead>
                <tr>
                  <th>Machine</th>
                  <th style={{textAlign:'right'}}>Availability</th>
                  <th style={{textAlign:'right'}}>Performance</th>
                  <th style={{textAlign:'right'}}>Quality</th>
                  <th style={{textAlign:'right'}}>OEE</th>
                  <th style={{textAlign:'right'}}>Downtime (min)</th>
                </tr>
              </thead>
              <tbody>
                {oee.map(r => {
                  const oeeColor = r.oee >= 75 ? 'var(--green)' : r.oee >= 55 ? 'var(--yellow)' : 'var(--red)'
                  return (
                    <tr key={r.machine_code}>
                      <td><span style={{fontFamily:'var(--font-mono)',fontWeight:600}}>{r.machine_code}</span></td>
                      <td style={{textAlign:'right',fontFamily:'var(--font-mono)'}}>{r.availability}%</td>
                      <td style={{textAlign:'right',fontFamily:'var(--font-mono)'}}>{r.performance}%</td>
                      <td style={{textAlign:'right',fontFamily:'var(--font-mono)'}}>{r.quality}%</td>
                      <td style={{textAlign:'right',fontFamily:'var(--font-mono)',fontWeight:700,color:oeeColor}}>{r.oee}%</td>
                      <td style={{textAlign:'right',fontFamily:'var(--font-mono)',color:'var(--muted)'}}>{r.dt_minutes}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* ── Downtime breakdown + pie ── */}
          <div className="two-col">
            <div>
              <SectionTitle>Downtime by Machine (minutes)</SectionTitle>
              <div className="card chart-card">
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={downtimeChart} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="machine_code" tick={{ fontSize: 11, fill: 'var(--muted)' }} />
                    <YAxis tick={{ fontSize: 11, fill: 'var(--muted)' }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="planned"   name="Planned"   fill="#4a8ae0" stackId="a" />
                    <Bar dataKey="unplanned" name="Unplanned" fill="#e05a4a" stackId="a" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div>
              <SectionTitle>Order Status Split</SectionTitle>
              <div className="card chart-card" style={{display:'flex',alignItems:'center',justifyContent:'center'}}>
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie data={orderPie} cx="50%" cy="50%" innerRadius={55} outerRadius={90}
                      dataKey="value" nameKey="name" label={({ name, value }) => `${name} ${value}`}
                      labelLine={false}>
                      {orderPie.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                    </Pie>
                    <Tooltip formatter={(v, n) => [v, n]} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* ── Top downtime reasons ── */}
          <SectionTitle>Top Downtime Reasons</SectionTitle>
          <div className="card table-card">
            <table>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Description</th>
                  <th>Category</th>
                  <th style={{textAlign:'right'}}>Occurrences</th>
                  <th style={{textAlign:'right'}}>Total Minutes</th>
                  <th>Share</th>
                </tr>
              </thead>
              <tbody>
                {(() => {
                  const totalMins = summary.top_reasons.reduce((s, r) => s + r.total_minutes, 0)
                  return summary.top_reasons.map(r => {
                    const share = totalMins ? Math.round(r.total_minutes / totalMins * 100) : 0
                    return (
                      <tr key={r.reason_code}>
                        <td><span style={{fontFamily:'var(--font-mono)',fontWeight:600}}>{r.reason_code}</span></td>
                        <td style={{color:'var(--ink)'}}>{r.description}</td>
                        <td>
                          <span className={`badge ${r.category === 'planned' ? 'badge-blue' : 'badge-red'}`}>
                            {r.category}
                          </span>
                        </td>
                        <td style={{textAlign:'right',fontFamily:'var(--font-mono)'}}>{r.occurrences}</td>
                        <td style={{textAlign:'right',fontFamily:'var(--font-mono)'}}>{r.total_minutes}</td>
                        <td>
                          <div style={{display:'flex',alignItems:'center',gap:8}}>
                            <div style={{width:80,height:5,background:'var(--surface3)',borderRadius:99,overflow:'hidden'}}>
                              <div style={{width:`${share}%`,height:'100%',background:r.category==='planned'?'#4a8ae0':'#e05a4a',borderRadius:99}} />
                            </div>
                            <span style={{fontSize:11,color:'var(--muted)'}}>{share}%</span>
                          </div>
                        </td>
                      </tr>
                    )
                  })
                })()}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
