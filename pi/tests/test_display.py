import io
from pathlib import Path

import pytest
from PIL import Image

from piframe.display.renderer import (
    FakeDisplay,
    EPD_WIDTH,
    EPD_HEIGHT,
    render_image,
    render_setup_screen,
    render_status,
    _ACEP_PALETTE,
)


def _make_image(w=800, h=480, color=(128, 64, 200)):
    return Image.new("RGB", (w, h), color=color)


def test_fake_display_dimensions():
    display = FakeDisplay()
    assert display.width == EPD_WIDTH
    assert display.height == EPD_HEIGHT


def test_getbuffer_correct_size():
    display = FakeDisplay()
    img = _make_image()
    buf = display.getbuffer(img)
    # 2 pixels per byte
    assert len(buf) == EPD_WIDTH * EPD_HEIGHT // 2


def test_getbuffer_only_palette_colors():
    display = FakeDisplay()
    img = _make_image()
    display.getbuffer(img)
    assert display.last_image is not None
    # Unique pixel values must be a subset of valid palette indices
    pixels = set(display.last_image.tobytes())
    valid_indices = set(range(len(_ACEP_PALETTE)))
    assert pixels.issubset(valid_indices)


def test_render_image_landscape(tmp_path):
    display = FakeDisplay(output_path=tmp_path / "out.png")
    img_path = tmp_path / "photo.jpg"
    _make_image(1000, 600).save(img_path, "JPEG")
    render_image(img_path, display)
    assert display.last_buf is not None


def test_render_image_portrait_rotated(tmp_path):
    display = FakeDisplay()
    img_path = tmp_path / "portrait.jpg"
    _make_image(480, 800).save(img_path, "JPEG")
    render_image(img_path, display)
    assert display.last_image is not None
    assert display.last_image.size == (EPD_WIDTH, EPD_HEIGHT)


def test_render_setup_screen():
    display = FakeDisplay()
    render_setup_screen("PiFrame-Setup", "http://192.168.4.1", display)
    assert display.last_buf is not None


def test_render_status():
    display = FakeDisplay()
    render_status("Test message", 75.0, display)
    assert display.last_buf is not None


def test_fake_display_saves_png(tmp_path):
    out = tmp_path / "out.png"
    display = FakeDisplay(output_path=out)
    img = _make_image()
    buf = display.getbuffer(img)
    display.display(buf)
    assert out.exists()
    saved = Image.open(out)
    assert saved.size == (EPD_WIDTH, EPD_HEIGHT)
