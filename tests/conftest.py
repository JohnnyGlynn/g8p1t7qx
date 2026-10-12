import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from weather_sensor_api import db
from weather_sensor_api.main import app


@pytest.fixture 
def connection() -> Iterator[sqlite3.Connection]:
    conn = db.connect(":memory:", check_same_thread=False)#test db path
    db.init_db(conn)
    yield conn
    conn.close()

@pytest.fixture
def client(connection: sqlite3.Connection) -> Iterator[TestClient]:
    app.dependency_overrides[db.get_conn] = lambda: connection
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

