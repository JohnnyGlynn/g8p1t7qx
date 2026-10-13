import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from weather_sensor_api import db
from weather_sensor_api.main import app


def test_sensor_aggregates(connection: sqlite3.Connection) -> None:
    db.insert_reading(
        connection, "Base_Station", 100, {"temperature": 10.0, "humidity": 67.0}
    )
    db.insert_reading(
        connection, "Turbine", 100, {"temperature": 9.0, "wind_speed": 10.0}
    )
    db.insert_reading(connection, "Turbine", 200, {"wind_speed": 20})

    rows = db.get_stats(
        connection,
        metrics=["temperature", "humidity", "wind_speed"],
        stat="avg",
        start_range=0,
        end_range=1000,
    )

    assert rows == [
        {"sensor_id": "Base_Station", "metric": "humidity", "value": 67.0, "count": 1},
        {
            "sensor_id": "Base_Station",
            "metric": "temperature",
            "value": 10.0,
            "count": 1,
        },
        {"sensor_id": "Turbine", "metric": "temperature", "value": 9.0, "count": 1},
        {"sensor_id": "Turbine", "metric": "wind_speed", "value": 15.0, "count": 2},
    ]


@pytest.mark.parametrize(
    ("stat", "expected"),
    [("min", 4.0), ("max", 16.0), ("sum", 20.0), ("avg", 10.0)],
)
def test_statistics(connection: sqlite3.Connection, stat: str, expected: float) -> None:
    db.insert_reading(connection, "Turbine", 10, {"temperature": 4.0})
    db.insert_reading(connection, "Turbine", 20, {"temperature": 16.0})

    [row] = db.get_stats(
        connection, metrics=["temperature"], stat=stat, start_range=0, end_range=100
    )

    assert row["value"] == expected


def test_sensor_filter(connection: sqlite3.Connection) -> None:
    db.insert_reading(connection, "Turbine", 10, {"temperature": 4.0})
    db.insert_reading(connection, "Base_Station", 15, {"temperature": 5.0})

    rows = db.get_stats(
        connection,
        metrics=["temperature"],
        stat="avg",
        start_range=0,
        end_range=20,
        sensor_ids=["Base_Station"],
    )

    assert [r["sensor_id"] for r in rows] == ["Base_Station"]


def test_real_connection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    with TestClient(app) as c:
        assert (
            c.get("/readings/stats", params={"metric": "temperature"}).status_code
            == 200
        )
