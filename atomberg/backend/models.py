"""
models.py – Pydantic request/response schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class OrderCreate(BaseModel):
    order_no:     str = Field(..., min_length=1, max_length=50)
    sku_code:     str = Field(..., min_length=1)
    qty_planned:  int = Field(..., gt=0)
    due_date:     str = Field(..., description="YYYY-MM-DD")
    priority:     str = Field(..., pattern="^(low|normal|high)$")
    status:       str = Field("planned", pattern="^(planned|released|in_progress|on_hold|completed|cancelled)$")
    machine_code: Optional[str] = None

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("due_date must be YYYY-MM-DD")
        return v


class OrderUpdate(BaseModel):
    sku_code:     Optional[str] = Field(None, min_length=1)
    qty_planned:  Optional[int] = Field(None, gt=0)
    due_date:     Optional[str] = None
    priority:     Optional[str] = Field(None, pattern="^(low|normal|high)$")
    status:       Optional[str] = Field(None, pattern="^(planned|released|in_progress|on_hold|completed|cancelled)$")
    machine_code: Optional[str] = None

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("due_date must be YYYY-MM-DD")
        return v
