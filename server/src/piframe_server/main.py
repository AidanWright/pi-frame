import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from piframe_server.models import Base
from piframe_server.routes.images import router as images_router
from piframe_server.routes.status import router as status_router

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:////var/lib/piframe-server/piframe.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="pi-frame server", lifespan=lifespan)
app.include_router(status_router)
app.include_router(images_router)
