from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, closing

from fastapi import FastAPI

from weather_sensor_api import db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    with closing(db.connect(db.DB_PATH)) as conn:
        db.init_db(conn)
    yield


app = FastAPI(title="Weather Sensor API", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
