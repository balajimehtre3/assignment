"""
seed.py – Load all six CSVs into the SQLite database.

Usage:
    python seed.py                  # uses default db path (./mes.db)
    python seed.py --db /path/to.db # custom path
    python seed.py --reset          # drop + recreate before loading
"""

import argparse
import csv
import os
import sqlite3
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def apply_schema(conn: sqlite3.Connection) -> None:
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()
    print("  Schema applied.")


def load_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return [row for row in csv.DictReader(f) if any(v.strip() for v in row.values())]


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def seed_machines(conn: sqlite3.Connection) -> None:
    rows = load_csv(CSV_FILES["machines"])
    conn.executemany(
        "INSERT OR REPLACE INTO machines (machine_code, name, target_units_per_hour) VALUES (:machine_code, :name, :target_units_per_hour)",
        rows,
    )
    conn.commit()
    print(f"  machines:         {len(rows)} rows")


def seed_skus(conn: sqlite3.Connection) -> None:
    rows = load_csv(CSV_FILES["skus"])
    conn.executemany(
        "INSERT OR REPLACE INTO skus (sku_code, description, std_cycle_time_sec) VALUES (:sku_code, :description, :std_cycle_time_sec)",
        rows,
    )
    conn.commit()
    print(f"  skus:             {len(rows)} rows")


def seed_downtime_reasons(conn: sqlite3.Connection) -> None:
    rows = load_csv(CSV_FILES["downtime_reasons"])
    conn.executemany(
        "INSERT OR REPLACE INTO downtime_reasons (reason_code, description, category) VALUES (:reason_code, :description, :category)",
        rows,
    )
    conn.commit()
    print(f"  downtime_reasons: {len(rows)} rows")


def seed_orders(conn: sqlite3.Connection) -> None:
    rows = load_csv(CSV_FILES["orders"])
    # machine_code may be empty string in CSV – normalise to None
    cleaned = []
    for r in rows:
        cleaned.append({
            "order_no":     r["order_no"].strip(),
            "sku_code":     r["sku_code"].strip(),
            "qty_planned":  int(r["qty_planned"].strip()),
            "due_date":     r["due_date"].strip(),
            "priority":     r["priority"].strip(),
            "status":       r["status"].strip(),
            "machine_code": r["machine_code"].strip() or None,
        })
    conn.executemany(
        """INSERT OR REPLACE INTO orders
           (order_no, sku_code, qty_planned, due_date, priority, status, machine_code)
           VALUES (:order_no, :sku_code, :qty_planned, :due_date, :priority, :status, :machine_code)""",
        cleaned,
    )
    conn.commit()
    print(f"  orders:           {len(cleaned)} rows")


def seed_unit_events(conn: sqlite3.Connection) -> None:
    rows = load_csv(CSV_FILES["unit_events"])
    BATCH = 5000
    total = 0
    for i in range(0, len(rows), BATCH):
        batch = rows[i : i + BATCH]
        conn.executemany(
            """INSERT OR IGNORE INTO unit_events
               (event_id, machine_code, order_no, completed_at, serial_no)
               VALUES (:event_id, :machine_code, :order_no, :completed_at, :serial_no)""",
            batch,
        )
        total += len(batch)
    conn.commit()
    print(f"  unit_events:      {total} rows")


def seed_downtime_events(conn: sqlite3.Connection) -> None:
    rows = load_csv(CSV_FILES["downtime_events"])
    cleaned = []
    for r in rows:
        cleaned.append({
            "downtime_id":  r["downtime_id"].strip(),
            "machine_code": r["machine_code"].strip(),
            "started_at":   r["started_at"].strip(),
            "ended_at":     r["ended_at"].strip() or None,
            "reason_code":  r["reason_code"].strip(),
            "note":         r.get("note", "").strip() or None,
        })
    conn.executemany(
        """INSERT OR REPLACE INTO downtime_events
           (downtime_id, machine_code, started_at, ended_at, reason_code, note)
           VALUES (:downtime_id, :machine_code, :started_at, :ended_at, :reason_code, :note)""",
        cleaned,
    )
    conn.commit()
    print(f"  downtime_events:  {len(cleaned)} rows")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed MES SQLite database")
    parser.add_argument("--db",    default=str(BASE_DIR / "mes.db"), help="Path to SQLite file")
    parser.add_argument("--reset", action="store_true",              help="Delete existing DB before seeding")
    args = parser.parse_args()

    db_path = args.db

    if args.reset and os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing DB: {db_path}")

    print(f"Seeding → {db_path}")
    conn = get_connection(db_path)

    apply_schema(conn)
    seed_machines(conn)
    seed_skus(conn)
    seed_downtime_reasons(conn)
    seed_orders(conn)
    seed_unit_events(conn)
    seed_downtime_events(conn)

    conn.close()
    print("Done ✓")


if __name__ == "__main__":
    main()
