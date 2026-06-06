import hashlib
import io
import os
from datetime import date
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image as PilImage
from sqlalchemy import select
from sqlalchemy.orm import Session

from piframe_server.acep import convert as acep_convert, to_png_bytes
from piframe_server.auth import require_admin, require_auth
from piframe_server.models import Image, ImageOut, PushRequest
from piframe_server.storage import delete_image, get_image_path, save_upload

router = APIRouter()


def get_db():
    from piframe_server.main import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _daily_image(db: Session) -> Optional[Image]:
    rows = db.execute(select(Image).order_by(Image.id)).scalars().all()
    if not rows:
        return None
    seed = int(hashlib.sha256(date.today().isoformat().encode()).hexdigest(), 16)
    return rows[seed % len(rows)]


@router.get("/api/images/daily")
def get_daily(db: Session = Depends(get_db)):
    img = _daily_image(db)
    if img is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No images available")
    path = get_image_path(img.filename)
    return FileResponse(path, media_type=img.mime_type, filename=img.original_name)


@router.get("/api/images", dependencies=[Depends(require_auth)])
def list_images(db: Session = Depends(get_db)) -> list[ImageOut]:
    rows = db.execute(select(Image).order_by(Image.upload_date.desc())).scalars().all()
    return [ImageOut.model_validate(r) for r in rows]


@router.post("/api/images", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def upload_image(file: UploadFile, db: Session = Depends(get_db)) -> ImageOut:
    data = file.file.read()
    try:
        img = PilImage.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid image file")

    png_bytes = to_png_bytes(acep_convert(img))
    filename = save_upload(png_bytes, ".png")
    row = Image(filename=filename, original_name=file.filename or filename, mime_type="image/png")
    db.add(row)
    db.commit()
    db.refresh(row)
    return ImageOut.model_validate(row)


@router.get("/api/images/{image_id}", dependencies=[Depends(require_auth)])
def get_image(image_id: int, db: Session = Depends(get_db)):
    row = db.get(Image, image_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    path = get_image_path(row.filename)
    return FileResponse(path, media_type=row.mime_type, filename=row.original_name)


@router.delete("/api/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_image_route(image_id: int, db: Session = Depends(get_db)):
    row = db.get(Image, image_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    delete_image(row.filename)
    db.delete(row)
    db.commit()


@router.post("/api/push", dependencies=[Depends(require_auth)])
def push_to_pi(body: PushRequest, db: Session = Depends(get_db)):
    tailnet = os.environ.get("TAILSCALE_TAILNET", "")
    if not tailnet:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="TAILSCALE_TAILNET not configured")

    pi_url = f"http://pi-frame.{tailnet}:8080"

    try:
        r = httpx.get(f"{pi_url}/health", timeout=5)
        r.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Pi unreachable: {exc}")

    payload: dict = {}
    if body.image_id is not None:
        row = db.get(Image, body.image_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        payload["image_id"] = body.image_id

    try:
        r = httpx.post(f"{pi_url}/refresh", json=payload, timeout=10)
        r.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Push failed: {exc}")

    return {"status": "pushed"}
