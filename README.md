# Weather Sensor API

REST service that can receive weather sensor readings, and return aggregate queries (min, max, sum, average) over select sensors, metrics and date/time ranges.

Constructed with FastAPI and SQLite3. Proof of concept that was scoped to about a weekend worth of work.

## Quick Start

In order to run this PoC, you'll need Python 3.13 and [uv](https://docs.astral.sh/uv/).

After cloning this repo, from its root:
```bash
uv sync
export WEATHER_SENSOR_API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
uv run python scripts/seed.py
echo $WEATHER_SENSOR_API_KEY
# This will give you the key that the server knows, and can be used in another terminal for cURL
# In your cURL terminal: export WEATHER_SENSOR_API_KEY=keydata
uv run fastapi dev src/weather_sensor_api/main.py --port 8080
```

Thanks to FastAPI, we get a free [OpenAPI docs endpoint](https://fastapi.tiangolo.com/reference/openapi/docs/).
This is available at http://localhost:8080/docs.

## If you do not want to use UV
```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e . pytest httpx2
fastapi dev src/weather_sensor_api/main.py --port 8080

```


### Configuration

-`WSA_DB_PATH`: is the location of the SQLite3 database file, if one is not provided it will default to weather.db.

-`WEATHER_SENSOR_API_KEY`: is required to access endpoints that could potentially be destructive (Write/Delete), if this key is not set, requests to these endpoints will be rejected.

## API

### Recording a sensor reading
`POST /sensors/{sensor_id}/readings` (Required: 'X-API-KEY' header)

```bash
curl -X POST localhost:8080/sensors/testSensor/readings \
    -H "X-API-KEY: $WEATHER_SENSOR_API_KEY" -H "Content-Type: application/json" \
    -d '{"recorded_at": "2026-10-12T09:00:00Z", "metrics": {"temperature": 12.0, "humidity": 72.0}}'
```
- `sensor_id`: Letters, Numbers, - and _ (Max 64)
- `metrics`: one or more (`temperature (c)`, `wind_speed (km/h)`, `humidity (%)`)
- `recorded_at`: optional timestamp **with timezone**, defaults to time of request.

### Query Statistic
`GET /readings/stats`

```bash
curl "localhost:8080/readings/stats?sensor_id=testSensor&metric=temperature&metric=humidity&stat=avg\
&start_range=2026-10-06T00:00:00Z&end_range=2026-10-13T00:00:00Z"

```

- `metric` Required, returns the aggregate for this metric, repeat metric for multiples
- `sensor_id` Not required, Providing one will scope it to a single, multiple to multiple, and empty for all
- `stat` Not Required, defaults to Average if (min, max, sum) are not provided.
- `start_range/end_range` Time range between 1-31 days, defaults to last 24 hours. Provide Both or neither, include timezone.

```json
{
  "start": "2026-10-06T00:00:00Z",
  "end": "2026-10-13T00:00:00Z",
  "stat": "avg",
  "results": [
    {"sensor_id": "testSensor", "metric": "humidity", "value": 72.0, "count": 1},
    {"sensor_id": "testSensor", "metric": "temperature", "value": 12.0, "count": 1}
  ]
}
```

Results are grouped by the sensor and metric, count providing how many readings were available.
The response shows the time range, so if the 24 hour default is engaged, you can see the exact window.

### Decommission a sensor
`DELETE /sensors/{sensor_id}` (Required: 'X-API-KEY' header)

```bash
curl -i -X DELETE localhost:8080/sensors/testSensor -H "X-API-KEY: $WEATHER_SENSOR_API_KEY"
```

Removes all sensor readings for a specified sensor, returning `204` on a delete or a `404` if the sensor isn't present.

### Validation and error handling

Input is validated at the request level, FastAPI maps failures to status codes, and exceptions are only caught where something meaningful can be done with them. Every error response has a `detail` field.

| Failure | Handled by | Result |
|---|---|---|
| Invalid input (unknown metric or stat, non-finite value, missing timezone, bad time range, malformed sensor ID, unknown query parameter) | pydantic schemas and path constraints | `422`, listing each failing field |
| Missing or incorrect API key on a write | `require_api_key` dependency | `401` |
| Decommissioning a sensor with no data | the endpoint | `404` |
| Failure partway through a write | a transaction per write | rolled back, no partial writes |
| Database error | `sqlite3.Error` handler | logged server-side, JSON `500`, no internals exposed |
| Anything unexpected | catch-all handler | logged server-side, JSON `500` |

## Testing and standards

This PoC uses:
[ruff](https://docs.astral.sh/ruff/) for linting and formatting.
[mypy](https://mypy.readthedocs.io/en/stable/) for static type checking.
[pytest](https://docs.pytest.org/en/stable/) for testing.

```
uv run ruff check .
uv run ruff format --check .
uv run mypy src scripts tests
uv run pytest
```

Most tests are run against an in-memory SQLite3 database, created for each test (:memory:), there is an explicit test case for a real connection against a temp db.

## Design

- FastAPI + pydantic: The project spec places an emphasis on validation, FastAPI allows for us to enforce types on the requests: Enums for metrics/stats, time-zone date times, and Schema level validation of those date windows. Invalid input becomes '422' by default, removing the need for explicit checks at the endpoint level, and as mentioned above, the free OpenAPI /docs.
- SQLite3: Data access is limited a single insert and an aggregate query. The SQL here is hand written as prepared statements, User input goes through `?` bound parameters. SQL interpolation only happens with aggregate functions, taken from a fixed list of allowed aggregates.
- Narrow table: One row per sensor, metric, timestamp and value. A new metric requires no change to the schema, just the list of accepted metrics.
- Timestamps as UTC epoch: Convert to epoch seconds at the api, range filter comparisons at the db. 
- Aggregates: Handled at the DB level, with no extra python needed.
- Connection per request: As SQLite3 connections are cheap, each request gets its own connection, removing the need for state management.
- API Auth: Potentially destructive endpoints such as Write and Delete have been gated by an API key, reads are open to query.
- Index: Composite index on (sensor_id, metric, recorded_at): Equality colyms firt and range last.

## Assumptions

- As per the spec, "the latest data should be queried" was defaulted to the last 24 hours of a sensors data.
- Date ranges are specified with a beginning and end or not at all.
- Sensors are not registered, it exists once a reading is received, as such this endpoint was gated with an API key.

## Extras outside of spec
- API key on potentially destructive endpoints.
- Sensor decommissioning with a DELETE endpoint.
- A sensor data seeding script.

## With more time
- PostgreSQL with migrations ( Could handle more concurrent writing than SQLite3)
- API level control of sensors, with a sensor registry, each sensor getting its own API key.
- Validation range on each metric.

