import sqlite3
from datetime import datetime, UTC
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, closing
from typing import Annotated

from fastapi import Depends, FastAPI, Path, status

from weather_sensor_api import db
from weather_sensor_api.schema import TakeReading, DisplayReading

# regex: Numbers, letters, hyphen, underscore, 1 or more
SensorId = Annotated[str, Path(min_length=1, max_length=64, pattern="^[A-Za-z0-9_-]+$")]
Connection = Annotated[sqlite3.Connection, Depends(db.get_conn)]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    with closing(db.connect(db.DB_PATH)) as conn:
        db.init_db(conn)
    yield


app = FastAPI(title="Weather Sensor API", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/sensors/{sensor_id}/readings", status_code=status.HTTP_201_CREATED)
def take_reading(
    sensor_id: SensorId, reading: TakeReading, conn: Connection
) -> DisplayReading:
    recorded_at = int(reading.recorded_at.timestamp())
    db.insert_reading(
        conn,
        sensor_id=sensor_id,
        recorded_at=recorded_at,
        metrics={metric.value: value for metric, value in reading.metrics.items()},
    )
    return DisplayReading(
        sensor_id=sensor_id,
        recorded_at=datetime.fromtimestamp(recorded_at, UTC),
        metrics=reading.metrics,
    )
