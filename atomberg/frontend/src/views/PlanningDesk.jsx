import { useState, useEffect, useCallback } from 'react'
import {
  getOrders, getOrder, createOrder, updateOrder, deleteOrder,
  getMachines, getSkus,
} from '../api.js'
import './PlanningDesk.css'

// ── helpers ──────────────────────────────────────────────────────────────────

const STATUS_LABELS = {
  planned: 'Planned', released: 'Released', in_progress: 'In Progress',
  on_hold: 'On Hold', completed: 'Completed', cancelled: 'Cancelled',
}
const PRIORITY_LABELS = { low: 'Low', normal: 'Normal', high: 'High' }

function statusBadge(s) {
  const cls = {
    planned: 'badge-gray', released: 'badge-blue', in_progress: 'badge-green',
    on_hold: 'badge-yellow', completed: 'badge-accent', cancelled: 'badge-red',
  }[s] || 'badge-gray'
  return <span className={`badge ${cls}`}>{STATUS_LABELS[s] || s}</span>
}
function priorityBadge(p) {
  const cls = { high: 'badge-red', normal: 'badge-yellow', low: 'badge-gray' }[p] || 'badge-gray'
  return <span className={`badge ${cls}`}>{PRIORITY_LABELS[p] || p}</span>
}

const EMPTY_FORM = {
  order_no: '', sku_code: '', qty_planned: '', due_date: '',
  priority: 'normal', status: 'planned', machine_code: '',
}

// ── OrderModal ────────────────────────────────────────────────────────────────

function OrderModal({ mode, initial, skus, machines, onSave, onClose }) {
  const [form, setForm] = useState(initial || EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState(null)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true); setErr(null)
    try {
      const payload = { ...form, qty_planned: Number(form.qty_planned) }
      if (!payload.machine_code) delete payload.machine_code
      if (mode === 'create') await createOrder(payload)
      else await updateOrder(form.order_no, payload)
      onSave()
    } catch (ex) {
      setErr(ex.message)
    } finally { setSaving(false) }
  }

  return (
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal">
        <div className="modal-header">
          <h2>{mode === 'create' ? 'New Order' : `Edit ${form.order_no}`}</h2>
          <button className="btn-ghost modal-close" onClick={onClose}>✕</button>
        </div>

        <form onSubmit={handleSubmit} className="modal-body">
          {err && <div className="form-error">{err}</div>}

          <div className="form-grid">
            <label className="form-field">
              <span>Order No</span>
              <input value={form.order_no} onChange={e => set('order_no', e.target.value)}
                required disabled={mode === 'edit'} placeholder="PO-2026-XXXX" />
            </label>

            <label className="form-field">
              <span>SKU</span>
              <select value={form.sku_code} onChange={e => set('sku_code', e.target.value)} required>
                <option value="">— select —</option>
                {skus.map(s => <option key={s.sku_code} value={s.sku_code}>{s.sku_code} · {s.description}</option>)}
              </select>
            </label>

            <label className="form-field">
              <span>Qty Planned</span>
              <input type="number" min="1" value={form.qty_planned}
                onChange={e => set('qty_planned', e.target.value)} required placeholder="e.g. 1200" />
            </label>

            <label className="form-field">
              <span>Due Date</span>
              <input type="date" value={form.due_date} onChange={e => set('due_date', e.target.value)} required />
            </label>

            <label className="form-field">
              <span>Priority</span>
              <select value={form.priority} onChange={e => set('priority', e.target.value)}>
                <option value="low">Low</option>
                <option value="normal">Normal</option>
                <option value="high">High</option>
              </select>
            </label>

            <label className="form-field">
              <span>Status</span>
              <select value={form.status} onChange={e => set('status', e.target.value)}>
                {Object.entries(STATUS_LABELS).map(([v, l]) =>
                  <option key={v} value={v}>{l}</option>
                )}
              </select>
            </label>

            <label className="form-field">
              <span>Machine (optional)</span>
              <select value={form.machine_code || ''} onChange={e => set('machine_code', e.target.value)}>
                <option value="">— unassigned —</option>
                {machines.map(m => <option key={m.machine_code} value={m.machine_code}>{m.machine_code} · {m.name}</option>)}
              </select>
            </label>
          </div>

          <div className="modal-actions">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Saving…' : mode === 'create' ? 'Create Order' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── OrderDetail ───────────────────────────────────────────────────────────────

function OrderDetail({ orderNo, onClose, onEdit, onDelete }) {
  const [order, setOrder] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getOrder(orderNo).then(d => { setOrder(d); setLoading(false) })
  }, [orderNo])

  if (loading) return (
    <div className="modal-overlay">
      <div className="modal" style={{display:'flex',alignItems:'center',justifyContent:'center',minHeight:200}}>
        <div className="spinner" />
      </div>
    </div>
  )

  const pct = order ? Math.min(100, Math.round((order.qty_completed / order.qty_planned) * 100)) : 0

  return (
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal modal-detail">
        <div className="modal-header">
          <div>
            <h2>{order.order_no}</h2>
            <div style={{fontSize:12, color:'var(--muted)', marginTop:2, fontFamily:'var(--font-mono)'}}>
              {order.sku_code}
            </div>
          </div>
          <button className="btn-ghost modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <div className="detail-grid">
            <div className="detail-row"><span>SKU</span><span>{order.sku_description}</span></div>
            <div className="detail-row"><span>Machine</span><span>{order.machine_code || '—'}</span></div>
            <div className="detail-row"><span>Due Date</span><span>{order.due_date}</span></div>
            <div className="detail-row"><span>Priority</span><span>{priorityBadge(order.priority)}</span></div>
            <div className="detail-row"><span>Status</span><span>{statusBadge(order.status)}</span></div>
            <div className="detail-row"><span>Planned</span><span>{order.qty_planned.toLocaleString()} units</span></div>
            <div className="detail-row"><span>Completed</span><span>{order.qty_completed.toLocaleString()} units</span></div>
            <div className="detail-row">
              <span>Progress</span>
              <span style={{display:'flex',alignItems:'center',gap:8,flex:1}}>
                <div style={{flex:1,height:6,background:'var(--surface3)',borderRadius:99,overflow:'hidden'}}>
                  <div style={{width:`${pct}%`,height:'100%',background:'var(--green)',borderRadius:99}} />
                </div>
                <span style={{fontSize:12,fontWeight:600,color:'var(--green)',minWidth:34}}>{pct}%</span>
              </span>
            </div>
            <div className="detail-row"><span>Std Cycle</span><span>{order.std_cycle_time_sec}s / unit</span></div>
          </div>

          <div className="modal-actions" style={{marginTop:24}}>
            <button className="btn-danger" onClick={() => onDelete(order.order_no)}>Delete</button>
            <div style={{flex:1}} />
            <button className="btn-ghost" onClick={onClose}>Close</button>
            <button className="btn-primary" onClick={() => onEdit(order)}>Edit</button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function PlanningDesk() {
  const [result, setResult] = useState({ items: [], total: 0, page: 1 })
  const [loading, setLoading] = useState(true)

  const [filters, setFilters] = useState({
    status: '', machine_code: '', priority: '', search: '', page: 1, page_size: 25,
  })

  const [machines, setMachines] = useState([])
  const [skus, setSkus] = useState([])

  const [modal, setModal]  = useState(null) // null | {type:'create'} | {type:'edit', order} | {type:'detail', orderNo}
  const [toast, setToast]  = useState(null)
  const [delConfirm, setDelConfirm] = useState(null)

  // load reference data once
  useEffect(() => {
    getMachines().then(setMachines)
    getSkus().then(setSkus)
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getOrders(filters)
      setResult(data)
    } catch (e) { showToast(e.message, 'error') }
    finally { setLoading(false) }
  }, [filters])

  useEffect(() => { load() }, [load])

  function showToast(msg, type = 'success') {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  function setFilter(k, v) {
    setFilters(f => ({ ...f, [k]: v, page: 1 }))
  }

  async function handleDelete(orderNo) {
    try {
      await deleteOrder(orderNo)
      showToast(`${orderNo} deleted`)
      setModal(null); setDelConfirm(null)
      load()
    } catch (e) { showToast(e.message, 'error') }
  }

  const totalPages = Math.ceil(result.total / filters.page_size)

  return (
    <div className="planning-wrap">
      {/* ── header ── */}
      <div className="planning-header">
        <div>
          <h1 className="page-title">Planning Desk</h1>
          <div className="page-sub">{result.total.toLocaleString()} orders</div>
        </div>
        <button className="btn-primary" onClick={() => setModal({ type: 'create' })}>+ New Order</button>
      </div>

      {/* ── filters ── */}
      <div className="filter-bar">
        <input
          placeholder="Search order / SKU…"
          value={filters.search}
          onChange={e => setFilter('search', e.target.value)}
          style={{ width: 220 }}
        />

        <select value={filters.status} onChange={e => setFilter('status', e.target.value)}>
          <option value="">All statuses</option>
          {Object.entries(STATUS_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>

        <select value={filters.priority} onChange={e => setFilter('priority', e.target.value)}>
          <option value="">All priorities</option>
          <option value="high">High</option>
          <option value="normal">Normal</option>
          <option value="low">Low</option>
        </select>

        <select value={filters.machine_code} onChange={e => setFilter('machine_code', e.target.value)}>
          <option value="">All machines</option>
          {machines.map(m => <option key={m.machine_code} value={m.machine_code}>{m.machine_code}</option>)}
        </select>

        <button className="btn-ghost" onClick={load} style={{marginLeft:'auto'}}>↻ Refresh</button>
      </div>

      {/* ── table ── */}
      <div className="table-wrap">
        {loading && <div className="table-loading"><div className="spinner" /></div>}
        <table>
          <thead>
            <tr>
              <th>Order No</th>
              <th>SKU</th>
              <th>Machine</th>
              <th>Due Date</th>
              <th>Priority</th>
              <th>Status</th>
              <th style={{textAlign:'right'}}>Progress</th>
            </tr>
          </thead>
          <tbody>
            {result.items.length === 0 && !loading && (
              <tr><td colSpan={7} style={{textAlign:'center',color:'var(--muted)',padding:40}}>No orders found</td></tr>
            )}
            {result.items.map(o => {
              const pct = Math.min(100, Math.round((o.qty_completed / o.qty_planned) * 100))
              return (
                <tr key={o.order_no} style={{cursor:'pointer'}} onClick={() => setModal({ type:'detail', orderNo: o.order_no })}>
                  <td><span className="mono">{o.order_no}</span></td>
                  <td>
                    <div className="mono" style={{fontSize:12}}>{o.sku_code}</div>
                    <div style={{fontSize:11,color:'var(--muted)'}}>{o.sku_description}</div>
                  </td>
                  <td className="mono">{o.machine_code || <span style={{color:'var(--muted)'}}>—</span>}</td>
                  <td className="mono">{o.due_date}</td>
                  <td>{priorityBadge(o.priority)}</td>
                  <td>{statusBadge(o.status)}</td>
                  <td>
                    <div style={{display:'flex',alignItems:'center',gap:8,justifyContent:'flex-end'}}>
                      <div style={{width:80,height:5,background:'var(--surface3)',borderRadius:99,overflow:'hidden'}}>
                        <div style={{width:`${pct}%`,height:'100%',background:'var(--green)',borderRadius:99}} />
                      </div>
                      <span style={{fontSize:11,color:'var(--muted)',minWidth:30,textAlign:'right'}}>{pct}%</span>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* ── pagination ── */}
      {totalPages > 1 && (
        <div className="pagination">
          <button className="btn-ghost" disabled={filters.page <= 1}
            onClick={() => setFilters(f => ({ ...f, page: f.page - 1 }))}>← Prev</button>
          <span style={{color:'var(--muted)',fontSize:13}}>Page {filters.page} of {totalPages}</span>
          <button className="btn-ghost" disabled={filters.page >= totalPages}
            onClick={() => setFilters(f => ({ ...f, page: f.page + 1 }))}>Next →</button>
        </div>
      )}

      {/* ── modals ── */}
      {modal?.type === 'create' && (
        <OrderModal mode="create" skus={skus} machines={machines}
          onSave={() => { setModal(null); showToast('Order created'); load() }}
          onClose={() => setModal(null)} />
      )}
      {modal?.type === 'edit' && (
        <OrderModal mode="edit" initial={modal.order} skus={skus} machines={machines}
          onSave={() => { setModal(null); showToast('Order updated'); load() }}
          onClose={() => setModal(null)} />
      )}
      {modal?.type === 'detail' && (
        <OrderDetail orderNo={modal.orderNo}
          onClose={() => setModal(null)}
          onEdit={order => setModal({ type: 'edit', order })}
          onDelete={no => setDelConfirm(no)} />
      )}

      {/* ── delete confirm ── */}
      {delConfirm && (
        <div className="modal-overlay">
          <div className="modal" style={{maxWidth:400}}>
            <div className="modal-header"><h2>Delete order?</h2></div>
            <div className="modal-body">
              <p style={{color:'var(--ink2)'}}>
                This will permanently delete <strong style={{color:'var(--ink)'}}>{delConfirm}</strong>.
                This cannot be undone.
              </p>
              <div className="modal-actions" style={{marginTop:24}}>
                <button className="btn-ghost" onClick={() => setDelConfirm(null)}>Cancel</button>
                <button className="btn-danger" onClick={() => handleDelete(delConfirm)}>Delete</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── toast ── */}
      {toast && (
        <div className={`toast toast-${toast.type}`}>{toast.msg}</div>
      )}
    </div>
  )
}
