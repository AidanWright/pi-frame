import io

from PIL import Image

_WIDTH = 800
_HEIGHT = 480

_PALETTE = [
    (0, 0, 0),       # black
    (255, 255, 255), # white
    (255, 255, 0),   # yellow
    (255, 0, 0),     # red
    (0, 0, 0),       # reserved (black)
    (0, 0, 255),     # blue
    (0, 255, 0),     # green
]


def convert(image: Image.Image) -> Image.Image:
    pal_image = Image.new("P", (1, 1))
    flat = []
    for rgb in _PALETTE:
        flat.extend(rgb)
    flat += [0, 0, 0] * (256 - len(_PALETTE))
    pal_image.putpalette(flat)

    src_w, src_h = image.size
    scale = max(_WIDTH / src_w, _HEIGHT / src_h)
    new_w, new_h = int(src_w * scale), int(src_h * scale)
    image = image.resize((new_w, new_h), Image.LANCZOS)
    left, top = (new_w - _WIDTH) // 2, (new_h - _HEIGHT) // 2
    image = image.crop((left, top, left + _WIDTH, top + _HEIGHT))

    return image.convert("RGB").quantize(palette=pal_image).convert("RGB")


def to_png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, "PNG")
    return buf.getvalue()
