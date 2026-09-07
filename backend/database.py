"""
database.py - PostgreSQL connection helpers using psycopg2.
Uses a simple per-request connection pattern (no connection pool needed at this scale).
"""

from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.extras

from config import DATABASE_URL


def get_conn() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn


@contextmanager
def db() -> Generator[psycopg2.extensions.connection, None, None]:
    conn = get_conn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def rows_to_list(cursor) -> list[dict]:
    """Fetch all rows from a cursor and return as plain dicts."""
    return [dict(row) for row in cursor.fetchall()]
