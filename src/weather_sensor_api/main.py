from fastapi import FastAPI

app = FastAPI(title="Weather Sensor API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
