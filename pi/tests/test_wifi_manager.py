import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

import piframe.wifi.manager as wm


@pytest.fixture(autouse=True)
def patch_networks_file(tmp_path, monkeypatch):
    networks_path = tmp_path / "networks.json"
    monkeypatch.setattr(wm, "NETWORKS_FILE", networks_path)
    return networks_path


def _iw_output(ssids: dict[str, int]) -> str:
    """Build a minimal iw scan output string."""
    lines = []
    for ssid, signal in ssids.items():
        lines.append(f"\tsignal: {signal}.00 dBm")
        lines.append(f"\tSSID: {ssid}")
    return "\n".join(lines)


def test_scan_visible_ssids():
    visible = {"HomeNet": -55, "CoffeeShop": -72}
    with patch.object(wm, "_run") as mock_run:
        mock_run.return_value = MagicMock(stdout=_iw_output(visible))
        result = wm.scan_visible_ssids()
    assert "HomeNet" in result
    assert "CoffeeShop" in result


def test_scan_returns_empty_on_failure():
    with patch.object(wm, "_run", side_effect=Exception("no wifi")):
        result = wm.scan_visible_ssids()
    assert result == {}


def test_load_known_networks_empty():
    assert wm.load_known_networks() == []


def test_save_and_load_network(patch_networks_file):
    wm.save_network("MyNet", "secret")
    networks = wm.load_known_networks()
    assert len(networks) == 1
    assert networks[0]["ssid"] == "MyNet"
    assert networks[0]["psk"] == "secret"


def test_save_network_updates_existing(patch_networks_file):
    wm.save_network("MyNet", "old")
    wm.save_network("MyNet", "new")
    networks = wm.load_known_networks()
    assert len(networks) == 1
    assert networks[0]["psk"] == "new"


def test_try_connect_success():
    with patch.object(wm, "_run") as mock_run, \
         patch.object(wm, "_has_ip", return_value=True), \
         patch("subprocess.Popen") as mock_popen, \
         patch("time.sleep"):
        result = wm.try_connect("TestNet", "pass", timeout=5)
    assert result is True


def test_try_connect_timeout():
    with patch.object(wm, "_run"), \
         patch.object(wm, "_has_ip", return_value=False), \
         patch("subprocess.Popen"), \
         patch("time.sleep"), \
         patch("time.monotonic", side_effect=[0, 100]):  # instantly past deadline
        result = wm.try_connect("TestNet", "pass", timeout=5)
    assert result is False


def test_enable_ap_mode_calls_hostapd(monkeypatch, tmp_path):
    procs = {}

    def fake_popen(cmd, **kwargs):
        m = MagicMock()
        procs[cmd[0]] = m
        return m

    with patch.object(wm, "_run"), \
         patch("subprocess.Popen", side_effect=fake_popen), \
         patch("time.sleep"), \
         patch("piframe.wifi.portal.create_portal_app") as mock_portal, \
         patch("threading.Thread"):
        mock_portal.return_value = MagicMock()
        wm.enable_ap_mode()

    assert "hostapd" in procs
    assert "dnsmasq" in procs


def test_disable_ap_mode():
    mock_proc = MagicMock()
    wm._hostapd_proc = mock_proc
    wm._dnsmasq_proc = mock_proc
    with patch.object(wm, "_run"):
        wm.disable_ap_mode()
    mock_proc.terminate.assert_called()
    assert wm._hostapd_proc is None


def test_run_connects_on_known_visible(patch_networks_file):
    wm.save_network("HomeNet", "secret")

    with patch.object(wm, "scan_visible_ssids", return_value={"HomeNet": -50}), \
         patch.object(wm, "try_connect", return_value=True) as mock_try:
        wm.run()

    mock_try.assert_called_once_with("HomeNet", "secret")


def test_run_falls_back_to_ap_then_connects(patch_networks_file):
    scan_call = {"n": 0}

    def fake_scan():
        scan_call["n"] += 1
        if scan_call["n"] == 1:
            return {}  # Nothing visible on first scan
        return {"NewNet": -55}  # Visible after setup

    def fake_enable_ap():
        # Simulate the portal saving credentials while AP is active
        wm.save_network("NewNet", "pass")

    with patch.object(wm, "scan_visible_ssids", side_effect=fake_scan), \
         patch.object(wm, "try_connect", return_value=True), \
         patch.object(wm, "enable_ap_mode", side_effect=fake_enable_ap), \
         patch.object(wm, "disable_ap_mode"):
        wm.run()
