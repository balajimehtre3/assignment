"""
routers/events.py – /unit-events, /downtime-events, /downtime-reasons endpoints
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Query
from database import db, rows_to_list

router = APIRouter(tags=["events"])


# ── Downtime reasons ──────────────────────────────────────────────────────────

@router.get("/downtime-reasons")
def list_downtime_reasons():
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM downtime_reasons ORDER BY reason_code"
        ).fetchall()
    return rows_to_list(rows)


# ── Unit events ───────────────────────────────────────────────────────────────

@router.get("/unit-events")
def list_unit_events(
    machine_code: Optional[str] = Query(None),
    order_no:     Optional[str] = Query(None),
    from_dt:      Optional[str] = Query(None, description="ISO datetime lower bound"),
    to_dt:        Optional[str] = Query(None, description="ISO datetime upper bound"),
    page:         int           = Query(1, ge=1),
    page_size:    int           = Query(100, ge=1, le=1000),
):
    clauses: list[str] = []
    params:  list[Any] = []

    if machine_code:
        clauses.append("machine_code = ?")
        params.append(machine_code)
    if order_no:
        clauses.append("order_no = ?")
        params.append(order_no)
    if from_dt:
        clauses.append("completed_at >= ?")
        params.append(from_dt)
    if to_dt:
        clauses.append("completed_at <= ?")
        params.append(to_dt)

    where  = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    offset = (page - 1) * page_size

    with db() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM unit_events {where}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM unit_events {where} ORDER BY completed_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

    return {"total": total, "page": page, "page_size": page_size, "items": rows_to_list(rows)}


# ── Downtime events ───────────────────────────────────────────────────────────

@router.get("/downtime-events")
def list_downtime_events(
    machine_code: Optional[str] = Query(None),
    reason_code:  Optional[str] = Query(None),
    category:     Optional[str] = Query(None, description="planned or unplanned"),
    from_dt:      Optional[str] = Query(None),
    to_dt:        Optional[str] = Query(None),
    page:         int           = Query(1, ge=1),
    page_size:    int           = Query(100, ge=1, le=500),
):
    clauses: list[str] = []
    params:  list[Any] = []

    if machine_code:
        clauses.append("de.machine_code = ?")
        params.append(machine_code)
    if reason_code:
        clauses.append("de.reason_code = ?")
        params.append(reason_code)
    if category:
        clauses.append("dr.category = ?")
        params.append(category)
    if from_dt:
        clauses.append("de.started_at >= ?")
        params.append(from_dt)
    if to_dt:
        clauses.append("de.started_at <= ?")
        params.append(to_dt)

    where  = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    offset = (page - 1) * page_size

    sql = f"""
        SELECT de.*, dr.description AS reason_description, dr.category
        FROM downtime_events de
        JOIN downtime_reasons dr ON dr.reason_code = de.reason_code
        {where}
        ORDER BY de.started_at DESC
    """

    with db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM ({sql})", params).fetchone()[0]
        rows  = conn.execute(f"{sql} LIMIT ? OFFSET ?", params + [page_size, offset]).fetchall()

    return {"total": total, "page": page, "page_size": page_size, "items": rows_to_list(rows)}
