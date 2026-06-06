"""
Main entry point for the piframe systemd service.
"""
import logging
import socket
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def _is_online() -> bool:
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except OSError:
        return False


def refresh(payload: dict | None = None) -> None:
    """Fetch and display the current daily image (or a pushed one)."""
    from piframe.battery import read_battery
    from piframe.client import fetch_daily_image
    from piframe.display.renderer import get_display, render_image, render_status

    display = get_display()
    display.init()

    battery = read_battery()
    battery_pct = battery.get("soc_pct")

    try:
        if payload and "image_path" in payload:
            img_path = Path(payload["image_path"])
        else:
            img_path = fetch_daily_image()

        render_image(img_path, display)
        logger.info("Display updated from %s", img_path)
    except Exception as exc:
        logger.error("Failed to update display: %s", exc)
        render_status(f"Error: {exc}", battery_pct, display)

    display.sleep()


def main() -> None:
    from piframe.rtc import sync_from_rtc, set_daily_wake
    from piframe.listener import start_listener

    sync_from_rtc()

    if not _is_online():
        logger.warning("No internet connection; skipping image fetch")
        from piframe.display.renderer import get_display, render_status
        display = get_display()
        display.init()
        render_status("No internet connection", None, display)
        display.sleep()
        sys.exit(1)

    # Start push listener (daemon thread; stays alive while main runs)
    start_listener(refresh_fn=refresh)

    # Fetch and display today's image
    refresh()

    # Sleep until tomorrow's update time
    set_daily_wake(hour=8)


if __name__ == "__main__":
    main()
