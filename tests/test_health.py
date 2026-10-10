from fastapi.testclient import TestClient

from weather_sensor_api.main import app

client = TestClient(app)

def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
