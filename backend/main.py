"""
main.py – Atomberg MES API entry point.

Run with:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS, SIMULATED_NOW
from routers import analytics, auth, events, floor, machines, orders, skus

app = FastAPI(
    title="Atomberg MES API",
    version="1.0.0",
    description="Order-to-Output factory data API. Simulated now: 2026-08-17T09:15:00",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,   # set via CORS_ORIGINS env var
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)        # /auth/*        — public
app.include_router(machines.router)    # /machines/*    — protected
app.include_router(skus.router)        # /skus          — protected
app.include_router(orders.router)      # /orders/*      — protected
app.include_router(events.router)      # /unit-events, /downtime-events — protected
app.include_router(floor.router)       # /floor/*       — protected
app.include_router(analytics.router)   # /analytics/*   — protected


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "simulated_now": SIMULATED_NOW.isoformat()}
