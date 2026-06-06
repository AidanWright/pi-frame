import hashlib
import hmac
import os
import secrets
import time

# Random on startup is intentional — sessions invalidate when the server restarts.
# Set PIFRAME_SECRET_KEY in the environment to persist sessions across restarts.
_SECRET = os.environ.get("PIFRAME_SECRET_KEY") or secrets.token_hex(32)
_MAX_AGE = 30 * 24 * 3600


def make_token(role: str) -> str:
    payload = f"{role}:{int(time.time())}"
    sig = hmac.new(_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def verify_token(token: str) -> str | None:
    """Returns role if token is valid and not expired, else None."""
    try:
        payload, sig = token.rsplit(":", 1)
        role, ts_str = payload.split(":", 1)
    except ValueError:
        return None
    expected = hmac.new(_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    if time.time() - int(ts_str) > _MAX_AGE:
        return None
    return role
