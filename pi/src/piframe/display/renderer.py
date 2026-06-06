import io
import logging
import os
from pathlib import Path
from typing import Optional, Protocol

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

EPD_WIDTH = 800
EPD_HEIGHT = 480

# ACeP 6-color palette in RGB order (matches epd7in3e palette table)
_ACEP_PALETTE = [
    (0, 0, 0),       # 0: black
    (255, 255, 255), # 1: white
    (255, 255, 0),   # 2: yellow
    (255, 0, 0),     # 3: red
    (0, 0, 0),       # 4: reserved (black)
    (0, 0, 255),     # 5: blue
    (0, 255, 0),     # 6: green
]


class DisplayProtocol(Protocol):
    width: int
    height: int

    def init(self) -> int: ...
    def getbuffer(self, image: Image.Image) -> list: ...
    def display(self, buf: list) -> None: ...
    def sleep(self) -> None: ...


class FakeDisplay:
    """In-process display stub for tests and development — no hardware required."""

    width = EPD_WIDTH
    height = EPD_HEIGHT

    def __init__(self, output_path: Optional[Path] = None):
        self._output_path = output_path
        self.last_image: Optional[Image.Image] = None
        self.last_buf: Optional[list] = None

    def init(self) -> int:
        return 0

    def getbuffer(self, image: Image.Image) -> list:
        pal_image = Image.new("P", (1, 1))
        flat = []
        for rgb in _ACEP_PALETTE:
            flat.extend(rgb)
        flat += [0, 0, 0] * (256 - len(_ACEP_PALETTE))
        pal_image.putpalette(flat)

        imwidth, imheight = image.size
        if imwidth == self.width and imheight == self.height:
            image_temp = image
        elif imwidth == self.height and imheight == self.width:
            image_temp = image.rotate(90, expand=True)
        else:
            image_temp = image.resize((self.width, self.height), Image.LANCZOS)

        image_6color = image_temp.convert("RGB").quantize(palette=pal_image)
        self.last_image = image_6color
        buf_6color = bytearray(image_6color.tobytes("raw"))

        buf = [0x00] * (self.width * self.height // 2)
        idx = 0
        for i in range(0, len(buf_6color), 2):
            buf[idx] = (buf_6color[i] << 4) + buf_6color[i + 1]
            idx += 1

        self.last_buf = buf
        return buf

    def display(self, buf: list) -> None:
        if self._output_path and self.last_image is not None:
            # Convert palette image back to RGB for saving
            self.last_image.convert("RGB").save(self._output_path)
            logger.debug("FakeDisplay saved to %s", self._output_path)

    def sleep(self) -> None:
        pass


def get_display(fake_output: Optional[Path] = None) -> DisplayProtocol:
    """Return real EPD if SPI device is accessible, otherwise FakeDisplay."""
    if os.path.exists("/dev/spidev0.0"):
        from piframe.display.epd7in3e import EPD
        return EPD()
    return FakeDisplay(fake_output)


def _fit_cover(image: Image.Image, width: int, height: int) -> Image.Image:
    """Resize image to cover the target dimensions, then center-crop."""
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
