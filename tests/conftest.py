import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from weather_sensor_api import db, auth
from weather_sensor_api.main import app


@pytest.fixture 
def connection() -> Iterator[sqlite3.Connection]:
    conn = db.connect(":memory:", check_same_thread=False)#test db path
    db.init_db(conn)
    yield conn
    conn.close()

# https://docs.pytest.org/en/stable/how-to/monkeypatch.html
@pytest.fixture
def client(connection: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(auth, "KEY", "testkey")
    app.dependency_overrides[db.get_conn] = lambda: connection
    yield TestClient(app, headers={"X-API-KEY": "testkey"})
    app.dependency_overrides.clear()

