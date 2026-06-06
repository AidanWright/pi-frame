import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

import piframe.client as client_mod


def _jpeg_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), (255, 0, 0)).save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture()
def piframe_env(tmp_path, monkeypatch):
    etc = tmp_path / "etc" / "piframe"
    etc.mkdir(parents=True)
    (etc / "server-url").write_text("http://piframe.example.com")
    (etc / "api-key").write_text("my-api-key")

    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setenv("PIFRAME_CACHE_DIR", str(cache))

    real_path = Path

    def fake_path(p):
        s = str(p)
        if s.startswith("/etc/piframe/"):
            return etc / real_path(s).name
        if s.startswith("/var/lib/piframe"):
            return cache / real_path(s).name
        return real_path(p)

    return etc, cache, fake_path


def test_fetch_daily_image_success(piframe_env):
    etc, cache, fake_path = piframe_env
    jpeg = _jpeg_bytes()

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.content = jpeg
    mock_response.headers = {"content-type": "image/jpeg"}

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get = MagicMock(return_value=mock_response)

    with patch("piframe.client.Path", side_effect=fake_path), \
         patch("piframe.client.httpx.Client", return_value=mock_client):
        result = client_mod.fetch_daily_image()

    assert result.exists()
    assert result.read_bytes() == jpeg
    # Verify the correct URL and header were used
    call_args = mock_client.get.call_args
    assert "/api/images/daily" in call_args[0][0]
    assert call_args[1]["headers"]["X-API-Key"] == "my-api-key"


def test_fetch_image_by_id_success(piframe_env):
    etc, cache, fake_path = piframe_env
    jpeg = _jpeg_bytes()

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.content = jpeg
    mock_response.headers = {"content-type": "image/jpeg"}

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get = MagicMock(return_value=mock_response)

    with patch("piframe.client.Path", side_effect=fake_path), \
         patch("piframe.client.httpx.Client", return_value=mock_client):
        result = client_mod.fetch_image_by_id(42)

    assert result.exists()
    assert result.read_bytes() == jpeg
    call_args = mock_client.get.call_args
    assert "/api/images/42" in call_args[0][0]
    assert call_args[1]["headers"]["X-API-Key"] == "my-api-key"


def test_fetch_daily_image_http_error(piframe_env):
    import httpx
    _, _, fake_path = piframe_env

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=MagicMock()
    )

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get = MagicMock(return_value=mock_response)

    with patch("piframe.client.Path", side_effect=fake_path), \
         patch("piframe.client.httpx.Client", return_value=mock_client), \
         pytest.raises(Exception):
        client_mod.fetch_daily_image()
