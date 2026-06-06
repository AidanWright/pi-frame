import logging
import os
from pathlib import Path
from typing import Optional, Protocol

from PIL import Image

logger = logging.getLogger(__name__)

EPD_WIDTH = 800
EPD_HEIGHT = 480

# RGB values must match the palette table in epd7in3e so quantization maps correctly
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
