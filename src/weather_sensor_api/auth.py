import os
import secrets
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

KEY = os.getenv("WEATHER_SENSOR_API_KEY")
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

def require_key(key:Annotated[str | None, Security(api_key_header)]) -> None:
    if KEY is None or key is None or not secrets.compare_digest(key, KEY):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "API key invalid")
