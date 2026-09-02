"""
main.py – Atomberg MES API entry point.

Wires together the FastAPI app, CORS middleware, and all routers.
All business logic lives in routers/; shared infrastructure in config.py,
database.py, and models.py.

Run with:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import SIMULATED_NOW
from routers import machines, skus, orders, events, floor, analytics

app = FastAPI(
    title="Atomberg MES API",
    version="1.0.0",
    description="Order-to-Output factory data API. Simulated now: 2026-08-17T09:15:00",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(machines.router)
app.include_router(skus.router)
app.include_router(orders.router)
app.include_router(events.router)
app.include_router(floor.router)
app.include_router(analytics.router)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "simulated_now": SIMULATED_NOW.isoformat()}
