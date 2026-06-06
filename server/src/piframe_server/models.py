from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, Date, DateTime, Integer, String, func
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
    scheduled_date = Column(Date, nullable=True, index=True)


class ImageOut(BaseModel):
    id: int
    original_name: str
    mime_type: str
    upload_date: datetime
    scheduled_date: Optional[date]

    model_config = {"from_attributes": True}


class ScheduleRequest(BaseModel):
    scheduled_date: date


class PushRequest(BaseModel):
    image_id: Optional[int] = None
