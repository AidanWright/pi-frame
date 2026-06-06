import os

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: str = Security(_header)) -> str:
    expected = os.environ.get("PIFRAME_API_KEY", "")
    if not expected:
        raise RuntimeError("PIFRAME_API_KEY env var not set")
    if key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return key
