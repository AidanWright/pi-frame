import logging
import subprocess
import threading
from typing import Callable, Optional

from flask import Flask, jsonify, request

logger = logging.getLogger(__name__)

_refresh_callback: Optional[Callable] = None


def get_tailscale_ip() -> str:
    """Falls back to 0.0.0.0 (all interfaces) if Tailscale is not running."""
    try:
        result = subprocess.run(
            ["tailscale", "ip", "-4"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        ip = result.stdout.strip()
        if ip:
            return ip
    except Exception as exc:
        logger.warning("Could not get Tailscale IP: %s", exc)
    return "0.0.0.0"


def create_listener_app(refresh_fn: Callable) -> Flask:
    global _refresh_callback
    _refresh_callback = refresh_fn

    app = Flask(__name__)

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/refresh", methods=["POST"])
    def refresh():
        payload = request.get_json(silent=True) or {}
        logger.info("Received push refresh request: %s", payload)
        t = threading.Thread(target=_refresh_callback, kwargs={"payload": payload}, daemon=True)
        t.start()
        return jsonify({"status": "accepted"}), 202

    @app.route("/upload", methods=["POST"])
    def upload():
        import os
        from pathlib import Path

        data = request.get_data()
        if not data:
            return jsonify({"error": "no data"}), 400

        cache_dir = Path(os.environ.get("PIFRAME_CACHE_DIR", "/var/lib/piframe"))
        cache_dir.mkdir(parents=True, exist_ok=True)
        dest = cache_dir / "pushed.jpg"
        dest.write_bytes(data)
        logger.info("Saved uploaded image to %s (%d bytes)", dest, len(data))

        t = threading.Thread(
            target=_refresh_callback,
            kwargs={"payload": {"image_path": str(dest)}},
            daemon=True,
        )
        t.start()
        return jsonify({"status": "accepted"}), 202

    return app


def run() -> None:
    """Entry point for the piframe-listener systemd service."""
    import time
    from piframe.main import refresh

    start_listener(refresh_fn=refresh)
    while True:
        time.sleep(3600)


def start_listener(refresh_fn: Callable, port: int = 8080) -> threading.Thread:
    app = create_listener_app(refresh_fn)
    host = get_tailscale_ip()

    def _run():
        logger.info("Starting push listener on %s:%d", host, port)
        app.run(host=host, port=port, debug=False, use_reloader=False)

    t = threading.Thread(target=_run, daemon=True, name="piframe-listener")
    t.start()
    return t
