"""
routers/skus.py – /skus endpoint
"""

from fastapi import APIRouter, Depends
from auth_deps import get_current_user
from database import db

router = APIRouter(prefix="/skus", tags=["skus"])


@router.get("")
def list_skus(current_user: dict = Depends(get_current_user)):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM skus ORDER BY sku_code")
            return [dict(r) for r in cur.fetchall()]
