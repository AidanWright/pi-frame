import io
from datetime import date
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


def test_daily_returns_an_image(client):
    _upload(client, name="a.jpg")
    _upload(client, name="b.jpg")
    r = client.get("/api/images/daily")
    assert r.status_code == 200


def test_daily_is_stable_within_day(client):
    _upload(client, name="a.jpg")
    _upload(client, name="b.jpg")
    r1 = client.get("/api/images/daily")
    r2 = client.get("/api/images/daily")
    assert r1.headers["content-disposition"] == r2.headers["content-disposition"]


def test_daily_varies_by_date(client):
    for i in range(10):
        _upload(client, name=f"{i}.jpg")

    with patch("piframe_server.routes.images.date") as mock_date:
        mock_date.today.return_value = date(2024, 1, 1)
        r1 = client.get("/api/images/daily")
        mock_date.today.return_value = date(2024, 1, 2)
        r2 = client.get("/api/images/daily")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.headers["content-disposition"] != r2.headers["content-disposition"]


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
