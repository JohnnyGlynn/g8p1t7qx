import sqlite3
import pytest
from typing import Any
from datetime import datetime, UTC, timedelta

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

def test_default_timestamp(client: TestClient) -> None:
    resp = client.post("/sensors/Turbine/readings", json={"metrics": {"wind_speed": 27.0}})

    assert resp.status_code == 201
    recorded_at = datetime.fromisoformat(resp.json()["recorded_at"])
    assert abs((datetime.now(UTC) - recorded_at).total_seconds()) < 5

@pytest.mark.parametrize(
        "payload",
        [
            {"metrics": {}},
            {"recorded_at": "2026-12-01T00:00:00Z"},
            {"metrics": {"not_a_metric": 1337.0}},
            {"metrics": {"wind_speed": "very_windy"}},
            {"recorded_at": "2026-12-01T00:00:00", "metrics": {"wind_speed": 27.0}},
            {"recorded_at": "2077-12-01T00:00:00Z", "metrics": {"wind_speed": 27.0}},
        ],
    )
def test_invalid_payloads(client: TestClient, payload: dict[str, Any]) -> None:
    assert client.post("sensors/turbine/readings", json=payload).status_code == 422

# STATS
def test_empty_return(client: TestClient) -> None:
    resp = client.get("/readings/stats", params={"metric": "temperature"})

    assert resp.status_code == 200
    assert resp.json()["results"] == []

def test_last_24_default(client: TestClient, connection: sqlite3.Connection) -> None:
    now = datetime.now(UTC)
    db.insert_reading(connection, sensor_id="Turbine", recorded_at=int(datetime.timestamp(now - timedelta(hours=2))), metrics={"temperature": 4.0})
    db.insert_reading(connection, sensor_id="Turbine", recorded_at=int(datetime.timestamp(now - timedelta(days=2))), metrics={"temperature": 8.0})

    resp = client.get("/readings/stats", params={"metric": "temperature"})

    assert resp.status_code == 200
    assert resp.json()["results"] == [
        {"sensor_id": "Turbine", "metric": "temperature", "value": 4.0, "count": 1}
    ]

def test_stats_specific_time_and_sensor(client: TestClient, connection: sqlite3.Connection) -> None:
    start_time = datetime(2026, 12, 1, tzinfo=UTC)
    for sensor, temp in [("Turbine", 4.0), ("Base_station", 5.0), ("Dock", 10.0)]:
        db.insert_reading(connection, sensor_id=sensor, recorded_at=int(datetime.timestamp(start_time + timedelta(hours=1))), metrics={"temperature": temp})

    resp = client.get(
        "/readings/stats",
        params={
            "metric": "temperature",
            "stat": "max",
            "sensor_id": ["Turbine", "Base_station"],
            "start_range": start_time.isoformat(),
            "end_range": (start_time + timedelta(days=7)).isoformat(),
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["stat"] == "max"
    assert [(r["sensor_id"], r["value"]) for r in body["results"]] == [("Base_station", 5.0), ("Turbine", 4.0)] #ordering alphabetically

@pytest.mark.parametrize(
    "params",
    [
        {},
        {"metric": "not_a_metric"},
        {"metric": "temperature", "sensor_id": "not a sensor!"},
        {"metric": "temperature", "stat": "not_a_stat"},
        {"metric": "temperature", "start": "2026-12-01T00:00:00Z"},
        {"metric": "temperature", "start": "2026-12-01T00:00:00Z", "end": "2026-12-12T00:00:00Z"},
        {"metric": "temperature", "start": "2026-12-01T00:00:00Z", "end": "2026-11-01T00:00:00Z"},
    ]
)
def test_invalid_queries(client: TestClient, params: dict[str, Any]) -> None:
    assert client.get("/readings/stats", params=params).status_code == 422

