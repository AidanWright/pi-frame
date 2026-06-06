import io
from PIL import Image as PilImage


def _make_jpeg() -> bytes:
    buf = io.BytesIO()
    PilImage.new("RGB", (10, 10), color=(255, 0, 0)).save(buf, format="JPEG")
    return buf.getvalue()


def test_daily_no_auth_required(client):
    r = client.get("/api/images/daily")
    assert r.status_code == 404  # no images yet, but auth not required


def test_list_requires_auth(client):
    r = client.get("/api/images")
    assert r.status_code == 401


def test_list_wrong_key(client):
    r = client.get("/api/images", headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


def test_list_correct_key(client):
    r = client.get("/api/images", headers={"X-API-Key": "test-key"})
    assert r.status_code == 200


def test_upload_requires_auth(client):
    data = _make_jpeg()
    r = client.post("/api/images", files={"file": ("photo.jpg", data, "image/jpeg")})
    assert r.status_code == 401


def test_delete_requires_auth(client):
    r = client.delete("/api/images/1")
    assert r.status_code == 401


def test_status_no_auth(client):
    r = client.get("/api/status")
    assert r.status_code == 200
