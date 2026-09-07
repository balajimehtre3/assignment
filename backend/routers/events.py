"""
routers/events.py – /unit-events, /downtime-events, /downtime-reasons endpoints
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from auth_deps import get_current_user
from database import db

router = APIRouter(tags=["events"])


# ── Downtime reasons ──────────────────────────────────────────────────────────

@router.get("/downtime-reasons")
def list_downtime_reasons(current_user: dict = Depends(get_current_user)):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM downtime_reasons ORDER BY reason_code")
            return [dict(r) for r in cur.fetchall()]


# ── Unit events ───────────────────────────────────────────────────────────────

@router.get("/unit-events")
def list_unit_events(
    machine_code: Optional[str] = Query(None),
    order_no:     Optional[str] = Query(None),
    from_dt:      Optional[str] = Query(None, description="ISO datetime lower bound"),
    to_dt:        Optional[str] = Query(None, description="ISO datetime upper bound"),
    page:         int           = Query(1, ge=1),
    page_size:    int           = Query(100, ge=1, le=1000),
    current_user: dict          = Depends(get_current_user),
):
    clauses: list[str] = []
    params:  list[Any] = []

    if machine_code:
        clauses.append("machine_code = %s"); params.append(machine_code)
    if order_no:
        clauses.append("order_no = %s");     params.append(order_no)
    if from_dt:
        clauses.append("completed_at >= %s"); params.append(from_dt)
    if to_dt:
        clauses.append("completed_at <= %s"); params.append(to_dt)

    where  = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    offset = (page - 1) * page_size

    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS cnt FROM unit_events {where}", params)
            total = cur.fetchone()["cnt"]
            cur.execute(
                f"SELECT * FROM unit_events {where} ORDER BY completed_at DESC LIMIT %s OFFSET %s",
                params + [page_size, offset],
            )
            items = [dict(r) for r in cur.fetchall()]

    return {"total": total, "page": page, "page_size": page_size, "items": items}


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
    current_user: dict          = Depends(get_current_user),
):
    clauses: list[str] = []
    params:  list[Any] = []

    if machine_code:
        clauses.append("de.machine_code = %s"); params.append(machine_code)
    if reason_code:
        clauses.append("de.reason_code = %s");  params.append(reason_code)
    if category:
        clauses.append("dr.category = %s");     params.append(category)
    if from_dt:
        clauses.append("de.started_at >= %s");  params.append(from_dt)
    if to_dt:
        clauses.append("de.started_at <= %s");  params.append(to_dt)

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
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS cnt FROM ({sql}) sub", params)
            total = cur.fetchone()["cnt"]
            cur.execute(f"{sql} LIMIT %s OFFSET %s", params + [page_size, offset])
            items = [dict(r) for r in cur.fetchall()]

    return {"total": total, "page": page, "page_size": page_size, "items": items}
