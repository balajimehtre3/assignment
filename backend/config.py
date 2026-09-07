import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql://{user}:{password}@{host}:{port}/{dbname}".format(
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "postgres"),
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "atomberg_mes"),
    ),
)


JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "token")
JWT_ALGORITHM:  str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES:  int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES",  "60"))
REFRESH_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 days

_raw_origins = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:4173",
)
CORS_ORIGINS: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

SIMULATED_NOW = datetime(2026, 8, 17, 9, 15, 0)
