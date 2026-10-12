import sqlite3
from datetime import datetime, UTC

from fastapi.testclient import TestClient

from weather_sensor_api import db

# READINGS
def test_take_reading_storage(connection: sqlite3.Connection, client: TestClient) -> None:

    resp = client.post(
        "/sensors/turbine/readings",
        json={
            "recorded_at": "2026-10-01T00:00:00Z",
            "metrics": {"temperature": 10.0, "wind_speed": 27.0},
        },
    )

    assert resp.status_code == 201
    assert resp.json()["metrics"] == {"temperature": 10.0, "wind_speed": 27.0}

    timestamp = int(datetime(2026, 10, 1, 00, tzinfo=UTC).timestamp())

    rows = db.get_stats(
        connection,
        metrics=["temperature", "wind_speed"],
        stat="sum",
        start_range=timestamp,
        end_range=timestamp + 1,
    )

    assert [(r["metric"], r["value"]) for r in rows] == [
        ("temperature", 10.0),
        ("wind_speed", 27.0),
    ]

# STATS
def test_empty_return(client: TestClient) -> None:
    resp = client.get("/readings/stats", params={"metric": "temperature"})

    assert resp.status_code == 200
    assert resp.json()["results"] == []

