"""
routers/analytics.py – /analytics/summary and /analytics/oee
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from auth_deps import get_current_user
from database import db

router = APIRouter(prefix="/analytics", tags=["analytics"])

SHIFT_HOURS = 8


def _period_days(from_date: str, to_date: str) -> int:
    from_d = datetime.strptime(from_date, "%Y-%m-%d").date()
    to_d   = datetime.strptime(to_date,   "%Y-%m-%d").date()
    return max(1, (to_d - from_d).days + 1)


@router.get("/summary")
def analytics_summary(
    from_date:    str  = Query(..., description="YYYY-MM-DD"),
    to_date:      str  = Query(..., description="YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user),
):
    from_dt = f"{from_date} 00:00:00"
    to_dt   = f"{to_date} 23:59:59"

    with db() as conn:
        # Units per machine
        with conn.cursor() as cur:
            cur.execute(
                """SELECT machine_code, COUNT(*) AS units_produced
                   FROM unit_events WHERE completed_at BETWEEN %s AND %s
                   GROUP BY machine_code""",
                (from_dt, to_dt),
            )
            units_by_machine = [dict(r) for r in cur.fetchall()]

        # Downtime by machine + category, clamped to period
        with conn.cursor() as cur:
            cur.execute(
                """SELECT de.machine_code, dr.category,
                          ROUND(SUM(
                              EXTRACT(EPOCH FROM (
                                  LEAST(COALESCE(de.ended_at, %s), %s) -
                                  GREATEST(de.started_at, %s)
                              )) / 60
                          )::numeric, 1) AS minutes
                   FROM downtime_events de
                   JOIN downtime_reasons dr ON dr.reason_code = de.reason_code
                   WHERE de.started_at < %s AND (de.ended_at IS NULL OR de.ended_at > %s)
                   GROUP BY de.machine_code, dr.category""",
                (to_dt, to_dt, from_dt, to_dt, from_dt),
            )
            downtime_by_machine = [dict(r) for r in cur.fetchall()]

        # Top downtime reasons
        with conn.cursor() as cur:
            cur.execute(
                """SELECT de.reason_code, dr.description, dr.category,
                          COUNT(*) AS occurrences,
                          ROUND(SUM(
                              EXTRACT(EPOCH FROM (
                                  LEAST(COALESCE(de.ended_at, %s), %s) -
                                  GREATEST(de.started_at, %s)
                              )) / 60
                          )::numeric, 1) AS total_minutes
                   FROM downtime_events de
                   JOIN downtime_reasons dr ON dr.reason_code = de.reason_code
                   WHERE de.started_at < %s AND (de.ended_at IS NULL OR de.ended_at > %s)
                   GROUP BY de.reason_code, dr.description, dr.category
                   ORDER BY total_minutes DESC""",
                (to_dt, to_dt, from_dt, to_dt, from_dt),
            )
            top_reasons = [dict(r) for r in cur.fetchall()]

        # Order status counts
        with conn.cursor() as cur:
            cur.execute(
                """SELECT status, COUNT(*) AS count FROM orders
                   WHERE due_date BETWEEN %s AND %s GROUP BY status""",
                (from_date, to_date),
            )
            order_summary = [dict(r) for r in cur.fetchall()]

        # Daily output per machine
        with conn.cursor() as cur:
            cur.execute(
                """SELECT DATE(completed_at) AS day, machine_code, COUNT(*) AS units
                   FROM unit_events WHERE completed_at BETWEEN %s AND %s
                   GROUP BY day, machine_code ORDER BY day""",
                (from_dt, to_dt),
            )
            daily_output = [dict(r) for r in cur.fetchall()]

        with conn.cursor() as cur:
            cur.execute("SELECT * FROM machines")
            machines = [dict(r) for r in cur.fetchall()]

    days = _period_days(from_date, to_date)
    machine_targets = {
        m["machine_code"]: m["target_units_per_hour"] * SHIFT_HOURS * days
        for m in machines
    }
    units_map = {r["machine_code"]: r["units_produced"] for r in units_by_machine}

    performance = [
        {
            "machine_code":    mc,
            "units_produced":  units_map.get(mc, 0),
            "target":          target,
            "achievement_pct": round(units_map.get(mc, 0) / target * 100, 1) if target else 0,
        }
        for mc, target in machine_targets.items()
    ]

    return {
        "period":        {"from": from_date, "to": to_date, "days": days},
        "performance":   performance,
        "downtime":      downtime_by_machine,
        "top_reasons":   top_reasons,
        "order_summary": order_summary,
        "daily_output":  [
            {**r, "day": str(r["day"])} for r in daily_output
        ],
    }


@router.get("/oee")
def analytics_oee(
    from_date:    str  = Query(..., description="YYYY-MM-DD"),
    to_date:      str  = Query(..., description="YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user),
):
    from_dt = f"{from_date} 00:00:00"
    to_dt   = f"{to_date} 23:59:59"

    days            = _period_days(from_date, to_date)
    planned_minutes = SHIFT_HOURS * 60 * days

    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM machines")
            machines = [dict(r) for r in cur.fetchall()]

        oee_rows = []
        for m in machines:
            mc = m["machine_code"]

            with conn.cursor() as cur:
                cur.execute(
                    """SELECT COALESCE(SUM(
                           EXTRACT(EPOCH FROM (
                               LEAST(COALESCE(ended_at, %s), %s) -
                               GREATEST(started_at, %s)
                           )) / 60
                       ), 0) AS dt_minutes
                       FROM downtime_events
                       WHERE machine_code = %s
                         AND started_at < %s AND (ended_at IS NULL OR ended_at > %s)""",
                    (to_dt, to_dt, from_dt, mc, to_dt, from_dt),
                )
                dt_minutes = float(cur.fetchone()["dt_minutes"])

            run_minutes  = max(0.0, planned_minutes - dt_minutes)
            availability = run_minutes / planned_minutes if planned_minutes > 0 else 0.0

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM unit_events WHERE machine_code = %s AND completed_at BETWEEN %s AND %s",
                    (mc, from_dt, to_dt),
                )
                units_produced = cur.fetchone()["cnt"]

            theoretical = m["target_units_per_hour"] * (run_minutes / 60)
            performance  = min(units_produced / theoretical, 1.0) if theoretical > 0 else 0.0
            quality      = 1.0

            oee_rows.append({
                "machine_code":      mc,
                "machine_name":      m["name"],
                "planned_minutes":   planned_minutes,
                "dt_minutes":        round(dt_minutes, 1),
                "run_minutes":       round(run_minutes, 1),
                "availability":      round(availability * 100, 1),
                "units_produced":    units_produced,
                "theoretical_units": round(theoretical),
                "performance":       round(performance * 100, 1),
                "quality":           100.0,
                "oee":               round(availability * performance * quality * 100, 1),
            })

    return oee_rows
