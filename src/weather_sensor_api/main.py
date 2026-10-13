import logging
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, closing
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request, status
from fastapi.responses import JSONResponse

from weather_sensor_api import auth, db
from weather_sensor_api.schema import (
    DAY,
    DisplayReading,
    DisplayStats,
    GetStats,
    StatResult,
    TakeReading,
)

RequireKey = Depends(auth.require_key)

# regex: Numbers, letters, hyphen, underscore, 1 or more
SensorId = Annotated[str, Path(min_length=1, max_length=64, pattern="^[A-Za-z0-9_-]+$")]
Connection = Annotated[sqlite3.Connection, Depends(db.get_conn)]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    with closing(db.connect(db.DB_PATH)) as conn:
        db.init_db(conn)
    yield


app = FastAPI(title="Weather Sensor API", lifespan=lifespan)

logger = logging.getLogger(__name__)


# db error
@app.exception_handler(sqlite3.Error)
async def handle_db_error(request: Request, exc: sqlite3.Error) -> JSONResponse:
    logger.exception("db error... request: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal db error"})


# catch all
@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled error... request: %s %s", request.method, request.url.path
    )
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/sensors/{sensor_id}/readings",
    status_code=status.HTTP_201_CREATED,
    dependencies=[RequireKey],
)
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


@app.delete(
    "/sensors/{sensor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[RequireKey],
)
def decommission_sensor(sensor_id: SensorId, conn: Connection) -> None:
    if db.decommission_sensor(conn, sensor_id) == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"sensor not found {sensor_id}")


@app.get("/readings/stats")
def get_stats(query: Annotated[GetStats, Query()], conn: Connection) -> DisplayStats:
    if query.start_range is not None and query.end_range is not None:
        start, end = query.start_range, query.end_range
    else:
        end = datetime.now(UTC)
        start = end - DAY

    rows = db.get_stats(
        conn,
        metrics=[m.value for m in query.metric],
        stat=query.stat.value,
        start_range=int(start.timestamp()),
        end_range=int(end.timestamp()),
        sensor_ids=query.sensor_id,
    )
    return DisplayStats(
        start_range=start,
        end_range=end,
        stat=query.stat,
        results=[StatResult.model_validate(row) for row in rows],
    )
