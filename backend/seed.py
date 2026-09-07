"""
seed.py – Load all CSVs into PostgreSQL and create a default admin user.

Usage:
    python seed.py                  # seeds using DATABASE_URL from .env
    python seed.py --reset          # drops all tables then re-creates and seeds
    python seed.py --admin-only     # only (re)creates the admin user
"""

import argparse
import csv
import sys
from pathlib import Path

import bcrypt
import hashlib
import psycopg2
import psycopg2.extras

# Load .env before importing config
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from config import DATABASE_URL

BASE_DIR   = Path(__file__).resolve().parent
SCHEMA_SQL = BASE_DIR / "schema.sql"
SEED_DIR   = Path(__file__).resolve().parent.parent.parent / "seed_data" / "seed_data"

CSV_FILES = {
    "machines":         SEED_DIR / "machines.csv",
    "skus":             SEED_DIR / "skus.csv",
    "downtime_reasons": SEED_DIR / "downtime_reasons.csv",
    "orders":           SEED_DIR / "orders.csv",
    "unit_events":      SEED_DIR / "unit_events.csv",
    "downtime_events":  SEED_DIR / "downtime_events.csv",
}

def _hash_password(plain: str) -> str:
    """SHA-256 pre-hash then bcrypt — handles passwords of any length."""
    digest = hashlib.sha256(plain.encode()).hexdigest().encode()
    return bcrypt.hashpw(digest, bcrypt.gensalt()).decode()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_conn():
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
    conn.autocommit = False
    return conn


def load_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if any(v.strip() for v in r.values())]


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def drop_all(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            DROP TABLE IF EXISTS
                unit_events, downtime_events, orders,
                downtime_reasons, skus, machines, users
            CASCADE
        """)
    conn.commit()
    print("  Dropped all tables.")


def apply_schema(conn) -> None:
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print("  Schema applied.")


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def seed_machines(conn) -> None:
    rows = load_csv(CSV_FILES["machines"])
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur,
            """INSERT INTO machines (machine_code, name, target_units_per_hour)
               VALUES %s ON CONFLICT (machine_code) DO UPDATE
               SET name = EXCLUDED.name,
                   target_units_per_hour = EXCLUDED.target_units_per_hour""",
            [(r["machine_code"], r["name"], int(r["target_units_per_hour"])) for r in rows],
        )
    conn.commit()
    print(f"  machines:         {len(rows)} rows")


def seed_skus(conn) -> None:
    rows = load_csv(CSV_FILES["skus"])
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur,
            """INSERT INTO skus (sku_code, description, std_cycle_time_sec)
               VALUES %s ON CONFLICT (sku_code) DO UPDATE
               SET description = EXCLUDED.description,
                   std_cycle_time_sec = EXCLUDED.std_cycle_time_sec""",
            [(r["sku_code"], r["description"], int(r["std_cycle_time_sec"])) for r in rows],
        )
    conn.commit()
    print(f"  skus:             {len(rows)} rows")


def seed_downtime_reasons(conn) -> None:
    rows = load_csv(CSV_FILES["downtime_reasons"])
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur,
            """INSERT INTO downtime_reasons (reason_code, description, category)
               VALUES %s ON CONFLICT (reason_code) DO UPDATE
               SET description = EXCLUDED.description,
                   category = EXCLUDED.category""",
            [(r["reason_code"], r["description"], r["category"]) for r in rows],
        )
    conn.commit()
    print(f"  downtime_reasons: {len(rows)} rows")


def seed_orders(conn) -> None:
    rows = load_csv(CSV_FILES["orders"])
    cleaned = [
        (
            r["order_no"].strip(),
            r["sku_code"].strip(),
            int(r["qty_planned"].strip()),
            r["due_date"].strip(),
            r["priority"].strip(),
            r["status"].strip(),
            r["machine_code"].strip() or None,
        )
        for r in rows
    ]
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur,
            """INSERT INTO orders
               (order_no, sku_code, qty_planned, due_date, priority, status, machine_code)
               VALUES %s ON CONFLICT (order_no) DO NOTHING""",
            cleaned,
        )
    conn.commit()
    print(f"  orders:           {len(cleaned)} rows")


def ensure_conn(conn):
    """Return a live connection, reconnecting if the server closed it."""
    try:
        conn.cursor().execute("SELECT 1")
        return conn
    except Exception:
        conn.close()
        return get_conn()


def seed_unit_events(conn) -> None:
    rows = load_csv(CSV_FILES["unit_events"])
    BATCH = 1000   # smaller batches — commit after each to avoid long-running txn
    total = 0
    for i in range(0, len(rows), BATCH):
        conn = ensure_conn(conn)   # reconnect if server dropped the connection
        batch = rows[i: i + BATCH]
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO unit_events
                   (event_id, machine_code, order_no, completed_at, serial_no)
                   VALUES %s ON CONFLICT (event_id) DO NOTHING""",
                [(r["event_id"], r["machine_code"], r["order_no"],
                  r["completed_at"], r["serial_no"]) for r in batch],
                page_size=BATCH,
            )
        conn.commit()          # commit each batch — keeps transaction small
        total += len(batch)
        print(f"    unit_events: {total}/{len(rows)} ...", end="\r", flush=True)
    print()  # newline after progress line
    print(f"  unit_events:      {total} rows")
    return conn


def seed_downtime_events(conn) -> None:
    rows = load_csv(CSV_FILES["downtime_events"])
    cleaned = [
        (
            r["downtime_id"].strip(),
            r["machine_code"].strip(),
            r["started_at"].strip(),
            r["ended_at"].strip() or None,
            r["reason_code"].strip(),
            r.get("note", "").strip() or None,
        )
        for r in rows
    ]
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur,
            """INSERT INTO downtime_events
               (downtime_id, machine_code, started_at, ended_at, reason_code, note)
               VALUES %s ON CONFLICT (downtime_id) DO NOTHING""",
            cleaned,
        )
    conn.commit()
    print(f"  downtime_events:  {len(cleaned)} rows")


def seed_admin_user(conn) -> None:
    """Create default users for each role. Safe to re-run."""
    default_users = [
        ("admin",      "admin@atomberg.local",      "admin123",      "admin"),
        ("planner",    "planner@atomberg.local",    "planner123",    "planner"),
        ("supervisor", "supervisor@atomberg.local", "supervisor123", "supervisor"),
        ("manager",    "manager@atomberg.local",    "manager123",    "manager"),
    ]
    with conn.cursor() as cur:
        for username, email, password, role in default_users:
            hashed = _hash_password(password)
            cur.execute(
                """INSERT INTO users (username, email, hashed_password, role)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (username) DO UPDATE
                   SET hashed_password = EXCLUDED.hashed_password,
                       role = EXCLUDED.role""",
                (username, email, hashed, role),
            )
    conn.commit()
    print("  users:            4 default accounts created")
    print("    admin / admin123")
    print("    planner / planner123")
    print("    supervisor / supervisor123")
    print("    manager / manager123")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Atomberg MES PostgreSQL database")
    parser.add_argument("--reset",      action="store_true", help="Drop all tables before seeding")
    parser.add_argument("--admin-only", action="store_true", help="Only seed/reset default users")
    args = parser.parse_args()

    print(f"Connecting → {DATABASE_URL[:40]}...")
    try:
        conn = get_conn()
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    if args.admin_only:
        seed_admin_user(conn)
        conn.close()
        print("Done ✓")
        return

    if args.reset:
        drop_all(conn)

    apply_schema(conn)
    seed_machines(conn)
    seed_skus(conn)
    seed_downtime_reasons(conn)
    seed_orders(conn)
    conn = seed_unit_events(conn)
    seed_downtime_events(conn)
    seed_admin_user(conn)

    conn.close()
    print("Done ✓")


if __name__ == "__main__":
    main()
