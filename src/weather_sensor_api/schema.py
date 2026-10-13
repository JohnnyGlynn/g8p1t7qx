from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StringConstraints,
    field_validator,
    model_validator,
)

SensorIdStr = Annotated[
    str, StringConstraints(min_length=1, max_length=64, pattern="^[A-Za-z0-9_-]+$")
]

TIME_SKEW = timedelta(seconds=60)
DAY = timedelta(days=1)
MONTH = timedelta(days=31)


class Metric(StrEnum):
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    WIND_SPEED = "wind_speed"


class Statistic(StrEnum):
    MIN = "min"
    MAX = "max"
    SUM = "sum"
    AVG = "avg"


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


class GetStats(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric: list[Metric] = Field(min_length=1)
    # provide a sensor for specifics, leave empty for all sensors
    sensor_id: list[SensorIdStr] = Field(default_factory=list)
    stat: Statistic = Statistic.AVG
    start_range: AwareDatetime | None = None
    end_range: AwareDatetime | None = None

    # https://pydantic.dev/docs/validation/dev/concepts/validators/
    @model_validator(mode="after")
    def time_range(self) -> Self:
        if (self.start_range is None) != (self.end_range is None):
            raise ValueError(
                "start_range and end_range are required, provide neither for Last 24hrs"
            )
        if (
            self.start_range is not None
            and self.end_range is not None
            and not DAY <= self.end_range - self.start_range <= MONTH
        ):
            raise ValueError("Range limited between 1 and 31 days")
        return self


class StatResult(BaseModel):
    sensor_id: str
    metric: Metric
    value: float
    count: int


class DisplayStats(BaseModel):
    start_range: datetime
    end_range: datetime
    stat: Statistic
    results: list[StatResult]


class DisplayReading(BaseModel):
    sensor_id: str
    recorded_at: datetime
    metrics: dict[Metric, float]
