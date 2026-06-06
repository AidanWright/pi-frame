from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False, unique=True)
    original_name = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    upload_date = Column(DateTime, nullable=False, server_default=func.now())


class ImageOut(BaseModel):
    id: int
    original_name: str
    mime_type: str
    upload_date: datetime

    model_config = {"from_attributes": True}


class PushRequest(BaseModel):
    image_id: Optional[int] = None
