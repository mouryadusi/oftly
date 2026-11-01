"""Upload validation, safe storage, and dominant-colour extraction (Pillow only)."""
import io
import re
import uuid
from PIL import Image, ImageOps, UnidentifiedImageError
from .config import media_dir
from .models import SAFE_IMG

MAX_BYTES = 8 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 40_000_000     # guards against decompression bombs

PALETTE = {"black": (25, 25, 25), "white": (245, 245, 242), "grey": (128, 128, 128), "beige": (222, 205, 175),
           "cream": (245, 238, 215), "brown": (110, 75, 45), "tan": (190, 150, 105), "khaki": (180, 170, 120),
           "navy": (25, 35, 80), "blue": (40, 90, 190), "light blue": (150, 190, 230), "denim": (70, 100, 140),
           "green": (50, 140, 70), "olive": (110, 115, 50), "teal": (30, 130, 130), "red": (200, 40, 40),
           "burgundy": (110, 25, 45), "pink": (235, 150, 180), "orange": (235, 130, 40), "yellow": (240, 210, 60),
           "mustard": (210, 165, 40), "purple": (120, 60, 160), "silver": (192, 192, 196), "gold": (200, 165, 70)}

class UploadError(Exception):
    def __init__(self, msg, status=400):
        super().__init__(msg)
        self.status = status

def nearest_name(rgb):
    return min(PALETTE, key=lambda n: sum((a - b) ** 2 for a, b in zip(PALETTE[n], rgb)))

def dominant_color(img):
    """Most common non-background colour, mapped to the nearest named colour. A *suggestion* only."""
    im = img.convert("RGB")
    im.thumbnail((96, 96))
    raw = im.tobytes()
    px = [tuple(raw[i:i + 3]) for i in range(0, len(raw), 3)]
    fg = [p for p in px if not all(v > 235 for v in p)]
    use = fg if len(fg) > len(px) * 0.15 else px
    strip = Image.new("RGB", (len(use), 1))
    strip.putdata(use)
    q = strip.quantize(colors=4, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    _, idx = max(q.getcolors())
    return nearest_name(tuple(pal[idx * 3: idx * 3 + 3]))

def save_upload(data: bytes):
    """Validate and re-encode an image as JPEG. Returns (filename, suggested_colour)."""
    if not data:
        raise UploadError("The file is empty.")
    if len(data) > MAX_BYTES:
        raise UploadError("Image is larger than 8 MB.", 413)
    try:
        probe = Image.open(io.BytesIO(data))
        if probe.format not in ("JPEG", "PNG", "WEBP"):
            raise UploadError("Only JPEG, PNG or WebP images are supported.")
        probe.verify()
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        img = img.convert("RGB")
    except UploadError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError, ValueError):
        raise UploadError("That file is not a valid image.")
    img.thumbnail((1600, 1600))
    name = f"{uuid.uuid4().hex}.jpg"
    img.save(media_dir() / name, "JPEG", quality=88)
    return name, dominant_color(img)

def remove_image(name):
    if name and SAFE_IMG.match(name):
        (media_dir() / name).unlink(missing_ok=True)
