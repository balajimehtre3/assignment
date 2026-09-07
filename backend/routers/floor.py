"""
routers/floor.py – /floor/snapshot  (wall display, no interaction needed)
"""

from fastapi import APIRouter, Depends
from auth_deps import get_current_user
from config import SIMULATED_NOW
from database import db

router = APIRouter(prefix="/floor", tags=["floor"])


@router.get("/snapshot")
def floor_snapshot(current_user: dict = Depends(get_current_user)):
    """
    One record per machine:
    - current in-progress order + completion progress
    - units completed today
    - active downtime event (if any)
    - availability % for today
    """
    sim_now   = SIMULATED_NOW
    today_str = sim_now.date().isoformat()
    day_start = f"{today_str} 00:00:00"
    sim_now_s = sim_now.isoformat()

    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM machines ORDER BY machine_code")
            machines = [dict(r) for r in cur.fetchall()]

        result = []
        for m in machines:
            mc = m["machine_code"]

            # Current active order
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT o.order_no, o.sku_code, s.description AS sku_description,
                              o.qty_planned, o.priority, o.status,
                              COUNT(ue.event_id) AS qty_completed
                       FROM orders o
                       JOIN skus s ON s.sku_code = o.sku_code
                       LEFT JOIN unit_events ue ON ue.order_no = o.order_no
                       WHERE o.machine_code = %s AND o.status = 'in_progress'
                       GROUP BY o.order_no, o.sku_code, s.description,
                                o.qty_planned, o.priority, o.status
                       LIMIT 1""",
                    (mc,),
                )
                order = cur.fetchone()

            # Units finished today
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM unit_events WHERE machine_code = %s AND completed_at >= %s",
                    (mc, day_start),
                )
                units_today = cur.fetchone()["cnt"]

            # Active downtime: started before sim_now and not yet ended (or ended after sim_now)
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT de.*, dr.description AS reason_description, dr.category
                       FROM downtime_events de
                       JOIN downtime_reasons dr ON dr.reason_code = de.reason_code
                       WHERE de.machine_code = %s
                         AND de.started_at <= %s
                         AND (de.ended_at IS NULL OR de.ended_at > %s)
                       ORDER BY de.started_at DESC LIMIT 1""",
                    (mc, sim_now_s, sim_now_s),
                )
                active_dt = cur.fetchone()

            # Downtime minutes today — clamp each event to [day_start, sim_now]
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
                         AND started_at < %s
                         AND (ended_at IS NULL OR ended_at > %s)""",
                    (sim_now_s, sim_now_s, day_start, mc, sim_now_s, day_start),
                )
                dt_minutes = float(cur.fetchone()["dt_minutes"])

            elapsed_minutes = sim_now.hour * 60 + sim_now.minute
            availability = round(
                max(0.0, (elapsed_minutes - dt_minutes) / elapsed_minutes * 100), 1
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
