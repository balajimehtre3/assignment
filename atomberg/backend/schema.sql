-- ============================================================
-- Atomberg MES  –  SQLite schema
-- ============================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- Reference tables
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS machines (
    machine_code          TEXT PRIMARY KEY,
    name                  TEXT NOT NULL,
    target_units_per_hour INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS skus (
    sku_code              TEXT PRIMARY KEY,
    description           TEXT NOT NULL,
    std_cycle_time_sec    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS downtime_reasons (
    reason_code           TEXT PRIMARY KEY,
    description           TEXT NOT NULL,
    category              TEXT NOT NULL CHECK (category IN ('planned', 'unplanned'))
);

-- ------------------------------------------------------------
-- Orders
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS orders (
    order_no              TEXT PRIMARY KEY,
    sku_code              TEXT NOT NULL REFERENCES skus(sku_code),
    qty_planned           INTEGER NOT NULL CHECK (qty_planned > 0),
    due_date              TEXT NOT NULL,          -- ISO-8601 date string
    priority              TEXT NOT NULL CHECK (priority IN ('low', 'normal', 'high')),
    status                TEXT NOT NULL CHECK (status IN ('planned', 'released', 'in_progress', 'on_hold', 'completed', 'cancelled')),
    machine_code          TEXT REFERENCES machines(machine_code),
    created_at            TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    updated_at            TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_orders_status        ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_machine_code  ON orders(machine_code);
CREATE INDEX IF NOT EXISTS idx_orders_due_date      ON orders(due_date);
CREATE INDEX IF NOT EXISTS idx_orders_priority      ON orders(priority);

-- ------------------------------------------------------------
-- Unit events  (one row per finished unit)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS unit_events (
    event_id              TEXT PRIMARY KEY,
    machine_code          TEXT NOT NULL REFERENCES machines(machine_code),
    order_no              TEXT NOT NULL REFERENCES orders(order_no),
    completed_at          TEXT NOT NULL,          -- ISO-8601 datetime
    serial_no             TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_unit_events_machine_code  ON unit_events(machine_code);
CREATE INDEX IF NOT EXISTS idx_unit_events_order_no      ON unit_events(order_no);
CREATE INDEX IF NOT EXISTS idx_unit_events_completed_at  ON unit_events(completed_at);

-- ------------------------------------------------------------
-- Downtime events
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS downtime_events (
    downtime_id           TEXT PRIMARY KEY,
    machine_code          TEXT NOT NULL REFERENCES machines(machine_code),
    started_at            TEXT NOT NULL,          -- ISO-8601 datetime
    ended_at              TEXT,                   -- NULL = still running
    reason_code           TEXT NOT NULL REFERENCES downtime_reasons(reason_code),
    note                  TEXT
);

CREATE INDEX IF NOT EXISTS idx_downtime_events_machine_code ON downtime_events(machine_code);
CREATE INDEX IF NOT EXISTS idx_downtime_events_started_at   ON downtime_events(started_at);
CREATE INDEX IF NOT EXISTS idx_downtime_events_reason_code  ON downtime_events(reason_code);
