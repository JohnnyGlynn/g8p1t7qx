import sqlite3
from collections.abc import Iterator

import pytest

from weather_sensor_api import db


@pytest.fixture
def connection() -> Iterator[sqlite3.Connection]:
    conn = db.connect(":memory:")#test db path
    db.init_db(conn)
    yield conn
    conn.close()


def test_sensor_aggregates(connection: sqlite3.Connection) -> None:
    db.insert_reading(connection, "Base_Station", 100, {"temperature": 10.0, "humidity": 67.0})
    db.insert_reading(connection, "Turbine", 100, {"temperature": 9.0, "wind_speed": 10.0})
    db.insert_reading(connection, "Turbine", 200, {"wind_speed": 20})

    rows = db.get_stats(
        connection,
        metrics=["temperature", "humidity", "wind_speed"],
        stat="avg",
        start=0,
        end=1000,
    )

    assert rows == [
        {"sensor_id": "Base_Station", "metric": "humidity", "value": 67.0, "count": 1},
        {"sensor_id": "Base_Station", "metric": "temperature", "value": 10.0, "count": 1},
        {"sensor_id": "Turbine", "metric": "temperature", "value": 9.0, "count": 1},
        {"sensor_id": "Turbine", "metric": "wind_speed", "value": 15.0, "count": 2},
    ]
