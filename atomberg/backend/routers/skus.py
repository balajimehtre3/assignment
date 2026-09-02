"""
routers/skus.py – /skus endpoint
"""

from fastapi import APIRouter
from database import db, rows_to_list

router = APIRouter(prefix="/skus", tags=["skus"])


@router.get("")
def list_skus():
    with db() as conn:
        rows = conn.execute("SELECT * FROM skus ORDER BY sku_code").fetchall()
    return rows_to_list(rows)
