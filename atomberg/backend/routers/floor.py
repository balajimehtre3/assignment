"""
routers/floor.py – /floor/snapshot endpoint (wall display, no interaction)
"""

from fastapi import APIRouter
from database import db, rows_to_list
from config import SIMULATED_NOW

router = APIRouter(prefix="/floor", tags=["floor"])


@router.get("/snapshot")
def floor_snapshot():
    """
    One record per machine containing:
    - current in-progress order and its completion progress
    - units completed today
    - active downtime event (if any)
    - availability % for today based on elapsed shift time
    """
    sim_now   = SIMULATED_NOW.isoformat()
    today_str = SIMULATED_NOW.date().isoformat()
    day_start = f"{today_str}T00:00:00"

    with db() as conn:
        machines = rows_to_list(conn.execute("SELECT * FROM machines").fetchall())

        result = []
        for m in machines:
            mc = m["machine_code"]

            # Current active order
            order = conn.execute(
                """SELECT o.order_no, o.sku_code, s.description AS sku_description,
                          o.qty_planned, o.priority, o.status,
                          COUNT(ue.event_id) AS qty_completed
                   FROM orders o
                   JOIN skus s ON s.sku_code = o.sku_code
                   LEFT JOIN unit_events ue ON ue.order_no = o.order_no
                   WHERE o.machine_code = ? AND o.status = 'in_progress'
                   GROUP BY o.order_no
                   LIMIT 1""",
                (mc,),
            ).fetchone()

            # Units finished today
            units_today = conn.execute(
                "SELECT COUNT(*) FROM unit_events WHERE machine_code = ? AND completed_at >= ?",
                (mc, day_start),
            ).fetchone()[0]

            # Active downtime: started before now and not yet ended (or ended after now)
            active_dt = conn.execute(
                """SELECT de.*, dr.description AS reason_description, dr.category
                   FROM downtime_events de
                   JOIN downtime_reasons dr ON dr.reason_code = de.reason_code
                   WHERE de.machine_code = ?
                     AND de.started_at <= ?
                     AND (de.ended_at IS NULL OR de.ended_at > ?)
                   ORDER BY de.started_at DESC LIMIT 1""",
                (mc, sim_now, sim_now),
            ).fetchone()

            # Downtime minutes today – clamp each event to [day_start, sim_now]
            dt_minutes = conn.execute(
                """SELECT COALESCE(SUM(
                       (JULIANDAY(CASE WHEN COALESCE(ended_at,?) < ? THEN COALESCE(ended_at,?) ELSE ? END)
                        - JULIANDAY(CASE WHEN started_at > ? THEN started_at ELSE ? END)
                       ) * 1440
                   ), 0)
                   FROM downtime_events
                   WHERE machine_code = ?
                     AND started_at < ?
                     AND (ended_at IS NULL OR ended_at > ?)""",
                (sim_now, sim_now, sim_now, sim_now,
                 day_start, day_start,
                 mc, sim_now, day_start),
            ).fetchone()[0]

            elapsed_minutes = SIMULATED_NOW.hour * 60 + SIMULATED_NOW.minute
            availability = round(
                max(0, (elapsed_minutes - dt_minutes) / elapsed_minutes * 100), 1
            ) if elapsed_minutes > 0 else 100.0

            result.append({
                "machine":          m,
                "current_order":    dict(order) if order else None,
                "units_today":      units_today,
                "active_downtime":  dict(active_dt) if active_dt else None,
                "availability_pct": availability,
                "dt_minutes_today": round(dt_minutes, 1),
            })

    return result
