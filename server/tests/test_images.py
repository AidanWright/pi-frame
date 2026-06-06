import io
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image as PilImage

KEY = "test-key"
HEADERS = {"X-API-Key": KEY}


def _jpeg(color=(100, 150, 200)) -> bytes:
    buf = io.BytesIO()
    PilImage.new("RGB", (20, 20), color=color).save(buf, format="JPEG")
    return buf.getvalue()


def _upload(client, data=None, name="photo.jpg"):
    data = data or _jpeg()
    return client.post(
        "/api/images",
        files={"file": (name, data, "image/jpeg")},
        headers=HEADERS,
    )


def test_upload_returns_201(client):
    r = _upload(client)
    assert r.status_code == 201
    body = r.json()
    assert body["original_name"] == "photo.jpg"
    assert body["mime_type"] == "image/jpeg"
    assert body["scheduled_date"] is None


def test_upload_invalid_file(client):
    r = client.post(
        "/api/images",
        files={"file": ("bad.jpg", b"not an image", "image/jpeg")},
        headers=HEADERS,
    )
    assert r.status_code == 422


def test_list_empty(client):
    r = client.get("/api/images", headers=HEADERS)
    assert r.status_code == 200
    assert r.json() == []


def test_list_after_upload(client):
    _upload(client, name="a.jpg")
    _upload(client, name="b.jpg")
    r = client.get("/api/images", headers=HEADERS)
    assert r.status_code == 200
    names = [i["original_name"] for i in r.json()]
    assert "a.jpg" in names and "b.jpg" in names


def test_daily_no_images_returns_404(client):
    r = client.get("/api/images/daily")
    assert r.status_code == 404


def test_daily_returns_most_recent(client):
    _upload(client, name="old.jpg")
    _upload(client, name="new.jpg")
    r = client.get("/api/images/daily")
    assert r.status_code == 200
    assert r.headers["content-disposition"].endswith('filename="new.jpg"')


def test_daily_prefers_scheduled_today(client):
    r1 = _upload(client, name="unscheduled.jpg")
    r2 = _upload(client, name="today.jpg")
    img_id = r2.json()["id"]

    today = date.today().isoformat()
    client.post(f"/api/images/{img_id}/schedule", json={"scheduled_date": today}, headers=HEADERS)

    r = client.get("/api/images/daily")
    assert r.status_code == 200
    assert r.headers["content-disposition"].endswith('filename="today.jpg"')


def test_schedule_and_get(client):
    r = _upload(client)
    img_id = r.json()["id"]
    future = (date.today() + timedelta(days=5)).isoformat()
    r2 = client.post(f"/api/images/{img_id}/schedule", json={"scheduled_date": future}, headers=HEADERS)
    assert r2.status_code == 200
    assert r2.json()["scheduled_date"] == future


def test_delete(client):
    r = _upload(client)
    img_id = r.json()["id"]
    r2 = client.delete(f"/api/images/{img_id}", headers=HEADERS)
    assert r2.status_code == 204
    r3 = client.get("/api/images", headers=HEADERS)
    assert r3.json() == []


def test_push_no_tailnet(client):
    r = client.post("/api/push", json={}, headers=HEADERS)
    assert r.status_code == 503


def test_push_pi_unreachable(client, monkeypatch):
    monkeypatch.setenv("TAILSCALE_TAILNET", "example.ts.net")
    import httpx
    with patch("piframe_server.routes.images.httpx.get", side_effect=httpx.ConnectError("unreachable")):
        r = client.post("/api/push", json={}, headers=HEADERS)
    assert r.status_code == 502


def test_push_success(client, monkeypatch):
    monkeypatch.setenv("TAILSCALE_TAILNET", "example.ts.net")
    mock_get = MagicMock()
    mock_get.return_value.raise_for_status = MagicMock()
    mock_post = MagicMock()
    mock_post.return_value.raise_for_status = MagicMock()
    with patch("piframe_server.routes.images.httpx.get", mock_get), \
         patch("piframe_server.routes.images.httpx.post", mock_post):
        r = client.post("/api/push", json={}, headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["status"] == "pushed"
