"""
database.py – SQLite connection helpers shared across all routers.
"""

import sqlite3
from contextlib import contextmanager
from typing import Generator

from config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()


def rows_to_list(rows) -> list[dict]:
    """Convert a list of sqlite3.Row objects to plain dicts."""
    return [dict(r) for r in rows]
