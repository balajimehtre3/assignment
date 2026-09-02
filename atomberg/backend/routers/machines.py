"""
routers/machines.py – /machines endpoints
"""

from fastapi import APIRouter, HTTPException, Path as FPath
from database import db, rows_to_list

router = APIRouter(prefix="/machines", tags=["machines"])


@router.get("")
def list_machines():
    with db() as conn:
        rows = conn.execute("SELECT * FROM machines ORDER BY machine_code").fetchall()
    return rows_to_list(rows)


@router.get("/{machine_code}")
def get_machine(machine_code: str = FPath(...)):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM machines WHERE machine_code = ?", (machine_code,)
        ).fetchone()
    if not row:
        raise HTTPException(404, f"Machine '{machine_code}' not found")
    return dict(row)
