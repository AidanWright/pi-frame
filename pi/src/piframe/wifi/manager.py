import json
import logging
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

NETWORKS_FILE = Path(os.environ.get("PIFRAME_NETWORKS_FILE", "/var/lib/piframe/networks.json"))
AP_SSID = "PiFrame-Setup"

# Cleared before entering AP mode so run() can detect when the portal saves new credentials.
_new_creds_event = threading.Event()
AP_IP = "192.168.4.1"
DHCP_RANGE = "192.168.4.2,192.168.4.20,24h"
PORTAL_PORT = 80
CONNECT_TIMEOUT = 30


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, **kwargs)


def scan_visible_ssids() -> dict[str, int]:
    """Return dict of {ssid: signal_level} from iw scan output."""
    try:
        result = _run(["iw", "wlan0", "scan"], capture_output=True, text=True, timeout=15)
    except Exception as exc:
        logger.warning("iw scan failed: %s", exc)
        return {}

    ssids: dict[str, int] = {}
    current_signal = 0
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("signal:"):
            try:
                current_signal = int(float(line.split()[1]))
            except (ValueError, IndexError):
                current_signal = -100
        elif line.startswith("SSID:"):
            ssid = line[5:].strip()
            if ssid:
                ssids[ssid] = current_signal
    return ssids


def load_known_networks() -> list[dict]:
    if not NETWORKS_FILE.exists():
        return []
    try:
        return json.loads(NETWORKS_FILE.read_text())
    except Exception:
        return []


def save_network(ssid: str, psk: str) -> None:
    networks = load_known_networks()
    for net in networks:
        if net.get("ssid") == ssid:
            net["psk"] = psk
            break
    else:
        networks.append({"ssid": ssid, "psk": psk})
    NETWORKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    NETWORKS_FILE.write_text(json.dumps(networks, indent=2))
    _new_creds_event.set()


def _write_wpa_conf(ssid: str, psk: str, path: str) -> None:
    conf = f"""ctrl_interface=/run/wpa_supplicant
update_config=1
country=US

network={{
    ssid="{ssid}"
    psk="{psk}"
    key_mgmt=WPA-PSK
}}
"""
    Path(path).write_text(conf)


def _has_ip(interface: str = "wlan0") -> bool:
    result = _run(["ip", "addr", "show", interface], capture_output=True, text=True)
    return "inet " in result.stdout


def try_connect(ssid: str, psk: str, timeout: int = CONNECT_TIMEOUT) -> bool:
    with tempfile.NamedTemporaryFile(suffix=".conf", delete=False, mode="w") as f:
        conf_path = f.name
    _write_wpa_conf(ssid, psk, conf_path)

    _run(["pkill", "-x", "wpa_supplicant"], capture_output=True)
    time.sleep(0.5)

    proc = subprocess.Popen(
        ["wpa_supplicant", "-i", "wlan0", "-c", conf_path, "-B"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(2)
        if _has_ip():
            _run(["dhcpcd", "wlan0"], capture_output=True)
            return True

    _run(["pkill", "-x", "wpa_supplicant"], capture_output=True)
    return False


_hostapd_proc: subprocess.Popen | None = None
_dnsmasq_proc: subprocess.Popen | None = None
_portal_thread: threading.Thread | None = None


def _write_hostapd_conf(path: str) -> None:
    conf = f"""interface=wlan0
driver=nl80211
ssid={AP_SSID}
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
"""
    Path(path).write_text(conf)


def enable_ap_mode() -> None:
    global _hostapd_proc, _dnsmasq_proc, _portal_thread

    _run(["pkill", "-x", "wpa_supplicant"], capture_output=True)
    _run(["pkill", "-x", "dhcpcd"], capture_output=True)
    time.sleep(0.5)

    _run(["ip", "addr", "flush", "dev", "wlan0"], capture_output=True)
    _run(["ip", "addr", "add", f"{AP_IP}/24", "dev", "wlan0"], capture_output=True)
    _run(["ip", "link", "set", "wlan0", "up"], capture_output=True)

    with tempfile.NamedTemporaryFile(suffix="-hostapd.conf", delete=False, mode="w") as f:
        conf_path = f.name
    _write_hostapd_conf(conf_path)
    _hostapd_proc = subprocess.Popen(
        ["hostapd", conf_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    _dnsmasq_proc = subprocess.Popen(
        [
            "dnsmasq",
            "--no-daemon",
            f"--interface=wlan0",
            f"--dhcp-range={DHCP_RANGE}",
            f"--address=/#/{AP_IP}",
            "--no-resolv",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    from piframe.wifi.portal import create_portal_app
    flask_app = create_portal_app()

    def _run_portal():
        flask_app.run(host="0.0.0.0", port=PORTAL_PORT, debug=False, use_reloader=False)

    _portal_thread = threading.Thread(target=_run_portal, daemon=True)
    _portal_thread.start()


def disable_ap_mode() -> None:
    global _hostapd_proc, _dnsmasq_proc

    if _hostapd_proc:
        _hostapd_proc.terminate()
        _hostapd_proc = None
    if _dnsmasq_proc:
        _dnsmasq_proc.terminate()
        _dnsmasq_proc = None

    _run(["ip", "addr", "flush", "dev", "wlan0"], capture_output=True)


def run(on_ap_mode_started=None) -> None:
    while True:
        visible = scan_visible_ssids()
        known = load_known_networks()

        matches = [n for n in known if n["ssid"] in visible]
        matches.sort(key=lambda n: visible.get(n["ssid"], -100), reverse=True)

        for net in matches:
            logger.info("Trying to connect to %s …", net["ssid"])
            if try_connect(net["ssid"], net["psk"]):
                logger.info("Connected to %s", net["ssid"])
                return

        logger.info("No known networks available; starting provisioning AP")
        _new_creds_event.clear()
        enable_ap_mode()
        if on_ap_mode_started:
            on_ap_mode_started()

        _new_creds_event.wait()

        disable_ap_mode()
