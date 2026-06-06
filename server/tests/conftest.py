import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("PIFRAME_API_KEY", "test-key")
os.environ.setdefault("PIFRAME_ADMIN_PASSWORD", "admin-pass")
os.environ.setdefault("PIFRAME_USER_PASSWORD", "user-pass")
os.environ.setdefault("STORAGE_PATH", "")  # will be overridden per-test


from piframe_server.models import Base
from piframe_server.routes.images import get_db


@pytest.fixture()
def storage_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path))
    return tmp_path


@pytest.fixture()
def db_engine(tmp_path):
    url = f"sqlite:///{tmp_path}/test.db"
    eng = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def client(db_engine, storage_dir, monkeypatch):
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    from piframe_server import main as main_mod
    monkeypatch.setattr(main_mod, "engine", db_engine)
    monkeypatch.setattr(main_mod, "SessionLocal", TestSession)

    from piframe_server.main import app

    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
