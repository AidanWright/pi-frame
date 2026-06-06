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


def test_login_admin(client):
    r = client.post("/auth/login", json={"password": "admin-pass"})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"
    assert "pf_session" in r.cookies


def test_login_user(client):
    r = client.post("/auth/login", json={"password": "user-pass"})
    assert r.status_code == 200
    assert r.json()["role"] == "user"


def test_login_wrong_password(client):
    r = client.post("/auth/login", json={"password": "wrong"})
    assert r.status_code == 401


def test_session_cookie_grants_list_access(client):
    client.post("/auth/login", json={"password": "admin-pass"})
    r = client.get("/api/images")
    assert r.status_code == 200


def test_user_role_cannot_upload(client):
    client.post("/auth/login", json={"password": "user-pass"})
    data = _make_jpeg()
    r = client.post("/api/images", files={"file": ("photo.jpg", data, "image/jpeg")})
    assert r.status_code == 403


def test_user_role_cannot_delete(client):
    client.post("/auth/login", json={"password": "user-pass"})
    r = client.delete("/api/images/1")
    assert r.status_code == 403


def test_logout_clears_session(client):
    client.post("/auth/login", json={"password": "admin-pass"})
    assert client.get("/api/images").status_code == 200
    client.post("/auth/logout")
    assert client.get("/api/images").status_code == 401
