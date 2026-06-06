import logging
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw

from piframe.display.hardware import DisplayProtocol

logger = logging.getLogger(__name__)


def _fit_cover(image: Image.Image, width: int, height: int) -> Image.Image:
    src_w, src_h = image.size
    scale = max(width / src_w, height / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    image = image.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - width) // 2
    top = (new_h - height) // 2
    return image.crop((left, top, left + width, top + height))


def render_image(img_path: Path, display: DisplayProtocol) -> None:
    image = Image.open(img_path).convert("RGB")
    image = _fit_cover(image, display.width, display.height)
    buf = display.getbuffer(image)
    display.display(buf)


def render_setup_screen(ssid: str, url: str, display: DisplayProtocol) -> None:
    canvas = Image.new("RGB", (display.width, display.height), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    try:
        import qrcode
        qr = qrcode.make(url)
        qr = qr.resize((200, 200), Image.NEAREST)
        canvas.paste(qr, (display.width - 220, (display.height - 200) // 2))
    except ImportError:
        logger.warning("qrcode library not available; skipping QR code")

    lines = [
        "pi-frame WiFi Setup",
        "",
        f"Connect to: {ssid}",
        "(open network, no password)",
        "",
        f"Then visit: {url}",
    ]
    y = 60
    for line in lines:
        draw.text((40, y), line, fill=(0, 0, 0))
        y += 40

    buf = display.getbuffer(canvas)
    display.display(buf)


def render_status(message: str, battery_pct: Optional[float], display: DisplayProtocol) -> None:
    canvas = Image.new("RGB", (display.width, display.height), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text((40, 40), message, fill=(0, 0, 0))
    if battery_pct is not None:
        draw.text((40, 100), f"Battery: {battery_pct:.0f}%", fill=(0, 0, 0))
    buf = display.getbuffer(canvas)
    display.display(buf)
