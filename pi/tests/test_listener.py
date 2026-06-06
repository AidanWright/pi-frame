import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from piframe.listener import create_listener_app


@pytest.fixture()
def listener_client(tmp_path, monkeypatch):
    monkeypatch.setenv("PIFRAME_CACHE_DIR", str(tmp_path))
    refresh_mock = MagicMock()
    app = create_listener_app(refresh_fn=refresh_mock)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, refresh_mock, tmp_path


def test_health(listener_client):
    client, _, _ = listener_client
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_refresh_accepted(listener_client):
    client, refresh_mock, _ = listener_client
    with patch("threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        r = client.post("/refresh", json={})
    assert r.status_code == 202
    assert r.get_json()["status"] == "accepted"


def test_upload_saves_file(listener_client):
    client, refresh_mock, tmp_path = listener_client
    data = b"\xff\xd8\xff\xe0fake jpeg data"
    with patch("threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        r = client.post("/upload", data=data, content_type="application/octet-stream")
    assert r.status_code == 202
    saved = tmp_path / "pushed.jpg"
    assert saved.exists()
    assert saved.read_bytes() == data


def test_upload_empty_returns_400(listener_client):
    client, _, _ = listener_client
    r = client.post("/upload", data=b"", content_type="application/octet-stream")
    assert r.status_code == 400
