"""
routers/machines.py – /machines endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Path as FPath
from auth_deps import get_current_user
from database import db

router = APIRouter(prefix="/machines", tags=["machines"])


@router.get("")
def list_machines(current_user: dict = Depends(get_current_user)):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM machines ORDER BY machine_code")
            return [dict(r) for r in cur.fetchall()]


@router.get("/{machine_code}")
def get_machine(
    machine_code: str = FPath(...),
    current_user: dict = Depends(get_current_user),
):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM machines WHERE machine_code = %s", (machine_code,))
            row = cur.fetchone()
    if not row:
        raise HTTPException(404, f"Machine '{machine_code}' not found")
    return dict(row)
