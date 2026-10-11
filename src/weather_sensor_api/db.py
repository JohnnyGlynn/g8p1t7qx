import os
import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

DB_PATH = os.getenv("WSA_DB_PATH", "weather.db")

SCHEMA = """
    CREATE TABLE IF NOT EXISTS readings (
        id INTEGER PRIMARY KEY,
        sensor_id TEXT NOT NULL,
        metric TEXT NOT NULL,
        value REAL NOT NULL,
        recorded_at INTEGER NOT NULL 
    );

    CREATE INDEX IF NOT EXISTS idx_readings ON readings (sensor_id, metric, recorded_at);
"""

# Allowed names to be interpolated in query
AGGREGATES = {"min": "MIN", "max": "MAX", "sum": "SUM", "avg": "AVG"}


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


# TODO: Populate DB with sample data here?
def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def get_conn() -> Iterator[sqlite3.Connection]:
    conn = connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def insert_reading(
    conn: sqlite3.Connection,
    sensor_id: str,
    recorded_at: int,
    metrics: Mapping[str, float],
) -> None:
    with conn:
        conn.executemany(
            "INSERT INTO readings (sensor_id, metric, value, recorded_at) VALUES (?,?,?,?)",
            [
                (sensor_id, metric, value, recorded_at)
                for metric, value in metrics.items()
            ],
        )


def get_stats(
    conn: sqlite3.Connection,
    *,
    metrics: Sequence[str],
    stat: str,
    start: int,
    end: int,
    sensor_ids: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    agg = AGGREGATES.get(stat)
    if agg is None:
        raise ValueError(f"statistic not supported: {stat}")

    sql = f"""
        SELECT sensor_id, metric, {agg}(value) AS value, COUNT(*) AS count
        FROM readings
        WHERE metric IN ({_placeholders(metrics)})
            AND recorded_at >= ? AND recorded_at < ?
    """

    params: list[object] = [*metrics, start, end]

    # multiple sensors
    if sensor_ids:
        sql += f" AND sensor_id IN ({_placeholders(sensor_ids)})"
        params.extend(sensor_ids)

    sql += " GROUP BY sensor_id, metric ORDER BY sensor_id, metric"
    return [dict(row) for row in conn.execute(sql, params)]


def _placeholders(values: Sequence[object]) -> str:
    return ", ".join("?" * len(values))
