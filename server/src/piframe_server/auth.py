import os

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from piframe_server.session import verify_token

_header = APIKeyHeader(name="X-API-Key", auto_error=False)
COOKIE_NAME = "pf_session"


def _resolve_role(request: Request, key: str) -> str | None:
    expected_key = os.environ.get("PIFRAME_API_KEY", "")
    if expected_key and key == expected_key:
        return "api-key"
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return verify_token(token)
    return None


def require_auth(request: Request, key: str = Security(_header)) -> str:
    role = _resolve_role(request, key)
    if not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return role


def require_admin(request: Request, key: str = Security(_header)) -> str:
    role = _resolve_role(request, key)
    if role not in ("api-key", "admin"):
        if not role:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return role
