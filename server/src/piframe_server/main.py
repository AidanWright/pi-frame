import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from piframe_server.models import Base
from piframe_server.routes.auth import router as auth_router
from piframe_server.routes.images import router as images_router
from piframe_server.routes.status import router as status_router

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:////var/lib/piframe-server/piframe.db")

if DATABASE_URL.startswith("sqlite:///"):
    Path(DATABASE_URL[len("sqlite:///"):]).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="pi-frame server", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(status_router)
app.include_router(images_router)
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(_STATIC_DIR / "index.html")
