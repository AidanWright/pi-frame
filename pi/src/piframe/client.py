import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

def _read_config() -> tuple[str, str]:
    """Return (server_url, api_key) from /etc/piframe/ files."""
    server_url = Path("/etc/piframe/server-url").read_text().strip()
    api_key = Path("/etc/piframe/api-key").read_text().strip()
    return server_url, api_key


def fetch_image_by_id(image_id: int) -> Path:
    """Download a specific image from the server by ID and cache it locally."""
    server_url, api_key = _read_config()
    url = f"{server_url.rstrip('/')}/api/images/{image_id}"

    logger.info("Fetching image %d from %s", image_id, url)
    with httpx.Client(timeout=30) as client:
        r = client.get(url, headers={"X-API-Key": api_key})
        r.raise_for_status()

    content_type = r.headers.get("content-type", "image/jpeg")
    ext = ".jpg" if "jpeg" in content_type else ".png"

    cache_dir = Path(os.environ.get("PIFRAME_CACHE_DIR", "/var/lib/piframe"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    dest = cache_dir / f"pushed_{image_id}{ext}"
    dest.write_bytes(r.content)
    logger.info("Saved image %d to %s", image_id, dest)
    return dest


def fetch_daily_image() -> Path:
    """Download today's image from the server and cache it locally."""
    server_url, api_key = _read_config()
    url = f"{server_url.rstrip('/')}/api/images/daily"

    logger.info("Fetching daily image from %s", url)
    with httpx.Client(timeout=30) as client:
        r = client.get(url, headers={"X-API-Key": api_key})
        r.raise_for_status()

    content_type = r.headers.get("content-type", "image/jpeg")
    ext = ".jpg" if "jpeg" in content_type else ".png"

    cache_dir = Path(os.environ.get("PIFRAME_CACHE_DIR", "/var/lib/piframe"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    dest = cache_dir / f"current{ext}"
    dest.write_bytes(r.content)
    logger.info("Saved daily image to %s", dest)
    return dest
