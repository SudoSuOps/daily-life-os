"""
DailyLifeOS · Layer 2 — the typed vault.

Storage-path-agnostic, stdlib-only (sqlite3), runs identically on any hardware shell
(ZimaCube / Synology / UGREEN / mini-PC / Jetson). The data dir is config-driven via
LD_DATA_DIR (default ~/.localdiabetic) — never a vendor-specific path. PHI lives here,
on the box, and never leaves: this module has no network code by design.
"""
import os, sqlite3, json, time, datetime as dt

DATA_DIR = os.environ.get("LD_DATA_DIR", os.path.expanduser("~/.localdiabetic"))
DB_PATH = os.path.join(DATA_DIR, "vault.db")

# The typed records — the 15 folders become structured rows you can query.
SCHEMA = """
CREATE TABLE IF NOT EXISTS appointment (
  id INTEGER PRIMARY KEY, provider TEXT, specialty TEXT, when_ts TEXT,
  location TEXT, notes TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS medication (
  id INTEGER PRIMARY KEY, name TEXT, dose TEXT, schedule TEXT,
  supply_count REAL, supply_unit TEXT, per_day REAL, refill_threshold_days REAL,
  last_refill TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS lab_result (
  id INTEGER PRIMARY KEY, test TEXT, value REAL, unit TEXT, when_ts TEXT,
  provider TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS document (
  id INTEGER PRIMARY KEY, title TEXT, doc_type TEXT, file_path TEXT,
  issuer TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS contact (
  id INTEGER PRIMARY KEY, name TEXT, role TEXT, phone TEXT, email TEXT,
  is_emergency INTEGER DEFAULT 0, created TEXT);
CREATE TABLE IF NOT EXISTS supply_item (
  id INTEGER PRIMARY KEY, name TEXT, count REAL, unit TEXT, per_day REAL,
  threshold REAL, created TEXT);
CREATE TABLE IF NOT EXISTS wound_photo (
  id INTEGER PRIMARY KEY, file_path TEXT, location TEXT, when_ts TEXT,
  notes TEXT, created TEXT);
"""

TABLES = ["appointment", "medication", "lab_result", "document", "contact", "supply_item", "wound_photo"]


def _now():
    # caller-stamped time (no Date.now surprises); ISO UTC
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class Vault:
    """The on-box data layer. Open it, add typed records, query them. No network, ever."""

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.cx = sqlite3.connect(self.db_path)
        self.cx.row_factory = sqlite3.Row
        self.cx.executescript(SCHEMA)
        self.cx.commit()

    def add(self, table, **fields):
        if table not in TABLES:
            raise ValueError(f"unknown record type: {table}")
        fields.setdefault("created", _now())
        cols = ",".join(fields)
        qs = ",".join("?" * len(fields))
        cur = self.cx.execute(f"INSERT INTO {table} ({cols}) VALUES ({qs})", list(fields.values()))
        self.cx.commit()
        return cur.lastrowid

    def all(self, table):
        return [dict(r) for r in self.cx.execute(f"SELECT * FROM {table}")]

    def count(self, table):
        return self.cx.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def query(self, sql, params=()):
        return [dict(r) for r in self.cx.execute(sql, params)]

    def close(self):
        self.cx.close()


if __name__ == "__main__":
    v = Vault()
    print(f"vault at {v.db_path}")
    for t in TABLES:
        print(f"  {t}: {v.count(t)} records")
    v.close()
