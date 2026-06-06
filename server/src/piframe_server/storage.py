import os
import uuid
from pathlib import Path


def get_storage_path() -> Path:
    p = Path(os.environ.get("STORAGE_PATH", "/var/lib/piframe-server/images"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_upload(data: bytes, suffix: str) -> str:
    filename = f"{uuid.uuid4()}{suffix}"
    dest = get_storage_path() / filename
    dest.write_bytes(data)
    return filename


def get_image_path(filename: str) -> Path:
    return get_storage_path() / filename


def delete_image(filename: str) -> None:
    p = get_storage_path() / filename
    p.unlink(missing_ok=True)
