import os
import sqlite3
from collections.abc import Iterator

DB_PATH = os.getenv("WSA_DB_PATH", "weather.db")

SCHEMA = """
    CREATE TABLE IF NOT EXISTS readings (
        id INTEGER PRIMARY_KEY,
        sensor_id TEXT NOT NULL,
        metric TEXT NOT NULL,
        value REAL NOT NULL,
        recorded_at INTEGER NOT NULL 
    );

    CREATE INDEX IF NOT EXISTS idx_readings ON readings (sensor_id, metric, recorded_at);
"""

def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

# TODO: Populate DB with sample data here?
def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)

def get_conn() ->Iterator[sqlite3.Connection]:
    conn = connect(DB_PATH) # TODO: Configurable path?
    try:
        yield conn
    finally:
        conn.close()

