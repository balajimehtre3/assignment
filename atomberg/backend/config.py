"""
config.py – Central configuration for the Atomberg MES backend.
"""

import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# SQLite database path – override with DB_PATH env var for deployment
DB_PATH = os.environ.get("DB_PATH", str(BASE_DIR / "mes.db"))

# The dataset is a frozen snapshot; treat this as "now" throughout the app
SIMULATED_NOW = datetime(2026, 8, 17, 9, 15, 0)
