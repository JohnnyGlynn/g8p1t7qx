import math
import random
from contextlib import closing
from datetime import UTC, datetime, timedelta

from weather_sensor_api import db
from weather_sensor_api.schema import Metric

SENSORS = {
        # sensor, temp, wind_speed, humidity
        "base_station": (10.0, 20.0, 30.0),
        "turbine": (9.0, 27.0, 34.0),
        "dock": (11.0, 21.0, 43.0),
        "greenhouse": (23.0, 3.0, 78.0),
}

DAYS = 30
SEED = 12345

def main() -> None:
    rng = random.Random(SEED)
    end = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)

    with closing(db.connect(db.DB_PATH)) as connection:
        db.init_db(connection)
        if connection.execute("SELECT 1 FROM readings LIMIT 1").fetchone():
            print("DB already exists, please delete it to seed with this script.")
            return

        for sensor_id, (temp, wind_speed, humidity) in SENSORS.items():
            for past in range(DAYS*24):
                at = end - timedelta(hours=past)
                '''
                Cyclical encoding
                turn a day into 24 hours, hour/24
                2 * pi for a circle
                sine wave to have a peak,
                shift the peak to 2pm ish
                '''
                daily = math.sin(2 * math.pi * (at.hour - 8) / 24)
                db.insert_reading(
                        connection,
                        sensor_id=sensor_id,
                        recorded_at=int(at.timestamp()),
                        metrics={
                            Metric.TEMPERATURE.value: round(temp + 4 * daily + rng.gauss(0,1), 1),
                            Metric.WIND_SPEED.value: round(max(0.0, rng.gauss(wind_speed, 5)), 1),
                            Metric.HUMIDITY.value: round(min(100.0, max(0.0, humidity - 12 * daily + rng.gauss(0, 4))), 1),
                            },
                        )
    print(f"{db.DB_PATH} has been seeded with {len(SENSORS)} sensors x {DAYS} with hourly readings")


if __name__ == "__main__":
    main()
