"""
routers/orders.py – /orders endpoints (full CRUD)
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Path as FPath
from database import db, rows_to_list
from models import OrderCreate, OrderUpdate

router = APIRouter(prefix="/orders", tags=["orders"])


def _fetch_order(order_no: str) -> dict:
    """Shared helper – returns a single order with sku info and qty_completed."""
    with db() as conn:
        row = conn.execute(
            """SELECT o.*,
                      s.description       AS sku_description,
                      s.std_cycle_time_sec,
                      COUNT(ue.event_id)  AS qty_completed
               FROM orders o
               JOIN skus s ON s.sku_code = o.sku_code
               LEFT JOIN unit_events ue ON ue.order_no = o.order_no
               WHERE o.order_no = ?
               GROUP BY o.order_no""",
            (order_no,),
        ).fetchone()
    if not row:
        raise HTTPException(404, f"Order '{order_no}' not found")
    return dict(row)


@router.get("")
def list_orders(
    status:       Optional[str] = Query(None),
    machine_code: Optional[str] = Query(None),
    priority:     Optional[str] = Query(None),
    due_before:   Optional[str] = Query(None, description="YYYY-MM-DD"),
    due_after:    Optional[str] = Query(None, description="YYYY-MM-DD"),
    search:       Optional[str] = Query(None, description="Search order_no or sku_code"),
    page:         int           = Query(1, ge=1),
    page_size:    int           = Query(50, ge=1, le=500),
):
    clauses: list[str] = []
    params:  list[Any] = []

    if status:
        clauses.append("o.status = ?")
        params.append(status)
    if machine_code:
        clauses.append("o.machine_code = ?")
        params.append(machine_code)
    if priority:
        clauses.append("o.priority = ?")
        params.append(priority)
    if due_before:
        clauses.append("o.due_date <= ?")
        params.append(due_before)
    if due_after:
        clauses.append("o.due_date >= ?")
        params.append(due_after)
    if search:
        clauses.append("(o.order_no LIKE ? OR o.sku_code LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    base_sql = f"""
        SELECT o.*,
               s.description          AS sku_description,
               s.std_cycle_time_sec,
               COUNT(ue.event_id)      AS qty_completed
        FROM orders o
        JOIN skus s ON s.sku_code = o.sku_code
        LEFT JOIN unit_events ue ON ue.order_no = o.order_no
        {where}
        GROUP BY o.order_no
        ORDER BY o.due_date ASC, o.priority DESC
    """

    offset = (page - 1) * page_size

    with db() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM ({base_sql})", params
        ).fetchone()[0]
        rows = conn.execute(
            f"{base_sql} LIMIT ? OFFSET ?", params + [page_size, offset]
        ).fetchall()

    return {
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "items":     rows_to_list(rows),
    }


@router.get("/{order_no}")
def get_order(order_no: str = FPath(...)):
    return _fetch_order(order_no)


@router.post("", status_code=201)
def create_order(body: OrderCreate):
    with db() as conn:
        if not conn.execute(
            "SELECT 1 FROM skus WHERE sku_code = ?", (body.sku_code,)
        ).fetchone():
            raise HTTPException(422, f"sku_code '{body.sku_code}' does not exist")

        if body.machine_code and not conn.execute(
            "SELECT 1 FROM machines WHERE machine_code = ?", (body.machine_code,)
        ).fetchone():
            raise HTTPException(422, f"machine_code '{body.machine_code}' does not exist")

        if conn.execute(
            "SELECT 1 FROM orders WHERE order_no = ?", (body.order_no,)
        ).fetchone():
            raise HTTPException(409, f"Order '{body.order_no}' already exists")

        conn.execute(
            """INSERT INTO orders
               (order_no, sku_code, qty_planned, due_date, priority, status, machine_code)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (body.order_no, body.sku_code, body.qty_planned,
             body.due_date, body.priority, body.status, body.machine_code),
        )
        conn.commit()

    return _fetch_order(body.order_no)


@router.patch("/{order_no}")
def update_order(order_no: str, body: OrderUpdate):
    updates: dict[str, Any] = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields provided to update")

    with db() as conn:
        if not conn.execute(
            "SELECT 1 FROM orders WHERE order_no = ?", (order_no,)
        ).fetchone():
            raise HTTPException(404, f"Order '{order_no}' not found")

        if "sku_code" in updates and not conn.execute(
            "SELECT 1 FROM skus WHERE sku_code = ?", (updates["sku_code"],)
        ).fetchone():
            raise HTTPException(422, f"sku_code '{updates['sku_code']}' does not exist")

        if "machine_code" in updates and updates["machine_code"] and not conn.execute(
            "SELECT 1 FROM machines WHERE machine_code = ?", (updates["machine_code"],)
        ).fetchone():
            raise HTTPException(422, f"machine_code '{updates['machine_code']}' does not exist")

        set_clause  = ", ".join(f"{k} = ?" for k in updates)
        set_clause += ", updated_at = strftime('%Y-%m-%dT%H:%M:%S', 'now')"
        conn.execute(
            f"UPDATE orders SET {set_clause} WHERE order_no = ?",
            [*updates.values(), order_no],
        )
        conn.commit()

    return _fetch_order(order_no)


@router.delete("/{order_no}", status_code=204)
def delete_order(order_no: str):
    with db() as conn:
        if not conn.execute(
            "SELECT 1 FROM orders WHERE order_no = ?", (order_no,)
        ).fetchone():
            raise HTTPException(404, f"Order '{order_no}' not found")
        # unit_events has a FK → orders, so delete child rows first
        conn.execute("DELETE FROM unit_events WHERE order_no = ?", (order_no,))
        conn.execute("DELETE FROM orders WHERE order_no = ?", (order_no,))
        conn.commit()
