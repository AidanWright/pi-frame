import os
import secrets

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from piframe_server.session import make_token

router = APIRouter()
COOKIE_NAME = "pf_session"
COOKIE_MAX_AGE = 30 * 24 * 3600


class LoginRequest(BaseModel):
    password: str


@router.post("/auth/login")
def login(body: LoginRequest, response: Response):
    admin_pass = os.environ.get("PIFRAME_ADMIN_PASSWORD", "")
    user_pass = os.environ.get("PIFRAME_USER_PASSWORD", "")

    if not admin_pass:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="PIFRAME_ADMIN_PASSWORD not configured")

    if admin_pass and secrets.compare_digest(body.password, admin_pass):
        role = "admin"
    elif user_pass and secrets.compare_digest(body.password, user_pass):
        role = "user"
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    response.set_cookie(COOKIE_NAME, make_token(role),
                        httponly=True, samesite="lax", max_age=COOKIE_MAX_AGE)
    return {"role": role}


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}
