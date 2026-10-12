from datetime import UTC, datetime, timedelta
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, Field, FiniteFloat, field_validator

TIME_SKEW = timedelta(seconds=60)


class Metric(StrEnum):
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    WIND_SPEED = "wind_speed"


class TakeReading(BaseModel):
    """factory defers datetime.now so the reading gets its own "now",
    rather than AwareDatetime =datetime.now where every reading would have the same timestamp
    """

    recorded_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    metrics: dict[Metric, FiniteFloat] = Field(min_length=1)

    @field_validator("recorded_at")
    @classmethod
    def no_timeskip(cls, value: datetime) -> datetime:
        if value > datetime.now(UTC) + TIME_SKEW:
            raise ValueError("reading cannot be from the future")
        return value


class DisplayReading(BaseModel):
    sensor_id: str
    recorded_at: datetime
    metrics: dict[Metric, float]
