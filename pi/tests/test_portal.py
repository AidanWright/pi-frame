import json
from pathlib import Path
from unittest.mock import patch

import pytest

import piframe.wifi.manager as wm
from piframe.wifi.portal import create_portal_app


@pytest.fixture()
def portal_client(tmp_path, monkeypatch):
    monkeypatch.setattr(wm, "NETWORKS_FILE", tmp_path / "networks.json")
    app = create_portal_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, tmp_path / "networks.json"


def test_index_renders(portal_client):
    client, _ = portal_client
    with patch("piframe.wifi.portal.scan_visible_ssids", return_value={"HomeNet": -55}):
        r = client.get("/")
    assert r.status_code == 200
    assert b"HomeNet" in r.data


def test_save_stores_credentials(portal_client):
    client, networks_file = portal_client
    with patch("piframe.wifi.manager.scan_visible_ssids", return_value={}):
        r = client.post("/save", data={"ssid": "MyWifi", "psk": "hunter2"})
    assert r.status_code == 200
    assert b"saved" in r.data.lower() or b"connect" in r.data.lower()
    networks = json.loads(networks_file.read_text())
    assert any(n["ssid"] == "MyWifi" for n in networks)


def test_save_empty_ssid_redirects(portal_client):
    client, _ = portal_client
    r = client.post("/save", data={"ssid": "", "psk": ""})
    assert r.status_code == 302
