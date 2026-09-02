"""
routers/analytics.py – /analytics/summary and /analytics/oee endpoints
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query
from database import db, rows_to_list

router = APIRouter(prefix="/analytics", tags=["analytics"])

SHIFT_HOURS = 8  # assumed shift length for target and OEE calculations


def _period_days(from_date: str, to_date: str) -> int:
    from_d = datetime.strptime(from_date, "%Y-%m-%d").date()
    to_d   = datetime.strptime(to_date,   "%Y-%m-%d").date()
    return max(1, (to_d - from_d).days + 1)


@router.get("/summary")
def analytics_summary(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date:   str = Query(..., description="YYYY-MM-DD"),
):
    """
    Period summary covering:
    - units produced vs target per machine
    - downtime minutes by machine and category (planned / unplanned)
    - top downtime reasons by total minutes
    - order status breakdown
    - daily output per machine for trend charts
    """
    from_dt = f"{from_date}T00:00:00"
    to_dt   = f"{to_date}T23:59:59"

    with db() as conn:
        # Units produced per machine in the period
        units_by_machine = rows_to_list(conn.execute(
            """SELECT machine_code, COUNT(*) AS units_produced
               FROM unit_events
               WHERE completed_at BETWEEN ? AND ?
               GROUP BY machine_code""",
            (from_dt, to_dt),
        ).fetchall())

        # Downtime minutes per machine per category, clamped to period bounds
        downtime_by_machine = rows_to_list(conn.execute(
            """SELECT de.machine_code, dr.category,
                      ROUND(SUM(
                          (JULIANDAY(CASE WHEN COALESCE(de.ended_at,?) < ? THEN COALESCE(de.ended_at,?) ELSE ? END)
                           - JULIANDAY(CASE WHEN de.started_at > ? THEN de.started_at ELSE ? END)
                          ) * 1440
                      ), 1) AS minutes
               FROM downtime_events de
               JOIN downtime_reasons dr ON dr.reason_code = de.reason_code
               WHERE de.started_at < ? AND (de.ended_at IS NULL OR de.ended_at > ?)
               GROUP BY de.machine_code, dr.category""",
            (to_dt, to_dt, to_dt, to_dt, from_dt, from_dt, to_dt, from_dt),
        ).fetchall())

        # Top downtime reasons by total lost minutes
        top_reasons = rows_to_list(conn.execute(
            """SELECT de.reason_code, dr.description, dr.category,
                      COUNT(*) AS occurrences,
                      ROUND(SUM(
                          (JULIANDAY(CASE WHEN COALESCE(de.ended_at,?) < ? THEN COALESCE(de.ended_at,?) ELSE ? END)
                           - JULIANDAY(CASE WHEN de.started_at > ? THEN de.started_at ELSE ? END)
                          ) * 1440
                      ), 1) AS total_minutes
               FROM downtime_events de
               JOIN downtime_reasons dr ON dr.reason_code = de.reason_code
               WHERE de.started_at < ? AND (de.ended_at IS NULL OR de.ended_at > ?)
               GROUP BY de.reason_code
               ORDER BY total_minutes DESC""",
            (to_dt, to_dt, to_dt, to_dt, from_dt, from_dt, to_dt, from_dt),
        ).fetchall())

        # Order status counts for orders due in the period
        order_summary = rows_to_list(conn.execute(
            """SELECT status, COUNT(*) AS count
               FROM orders
               WHERE due_date BETWEEN ? AND ?
               GROUP BY status""",
            (from_date, to_date),
        ).fetchall())

        # Daily output per machine for trend line chart
        daily_output = rows_to_list(conn.execute(
            """SELECT DATE(completed_at) AS day, machine_code, COUNT(*) AS units
               FROM unit_events
               WHERE completed_at BETWEEN ? AND ?
               GROUP BY day, machine_code
               ORDER BY day""",
            (from_dt, to_dt),
        ).fetchall())

        machines = rows_to_list(conn.execute("SELECT * FROM machines").fetchall())

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
        "daily_output":  daily_output,
    }


@router.get("/oee")
def analytics_oee(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date:   str = Query(..., description="YYYY-MM-DD"),
):
    """
    Simplified OEE per machine for the selected period.

    Availability = run_time / planned_time
    Performance  = actual_units / (target_rate × run_hours)   [capped at 100%]
    Quality      = 1.0  (no reject data in this dataset)
    OEE          = Availability × Performance × Quality
    """
    from_dt = f"{from_date}T00:00:00"
    to_dt   = f"{to_date}T23:59:59"

    days            = _period_days(from_date, to_date)
    planned_minutes = SHIFT_HOURS * 60 * days

    with db() as conn:
        machines = rows_to_list(conn.execute("SELECT * FROM machines").fetchall())

        oee_rows = []
        for m in machines:
            mc = m["machine_code"]

            # Total downtime minutes in period, clamped to period bounds
            dt_minutes = conn.execute(
                """SELECT COALESCE(SUM(
                       (JULIANDAY(CASE WHEN COALESCE(ended_at,?) < ? THEN COALESCE(ended_at,?) ELSE ? END)
                        - JULIANDAY(CASE WHEN started_at > ? THEN started_at ELSE ? END)
                       ) * 1440
                   ), 0)
                   FROM downtime_events
                   WHERE machine_code = ?
                     AND started_at < ? AND (ended_at IS NULL OR ended_at > ?)""",
                (to_dt, to_dt, to_dt, to_dt, from_dt, from_dt, mc, to_dt, from_dt),
            ).fetchone()[0]

            run_minutes  = max(0, planned_minutes - dt_minutes)
            availability = run_minutes / planned_minutes if planned_minutes > 0 else 0

            units_produced = conn.execute(
                """SELECT COUNT(*) FROM unit_events
                   WHERE machine_code = ? AND completed_at BETWEEN ? AND ?""",
                (mc, from_dt, to_dt),
            ).fetchone()[0]

            theoretical = m["target_units_per_hour"] * (run_minutes / 60)
            performance  = min(units_produced / theoretical, 1.0) if theoretical > 0 else 0
            quality      = 1.0  # no scrap/reject data available

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
