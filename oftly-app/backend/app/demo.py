"""Original generated demo wardrobe: flat illustrations drawn with Pillow (no third-party images)."""
import uuid
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps
from .config import media_dir
from .images import PALETTE

# name, category, colour, formality, style, occasions, seasons, pattern
DEMO = [
    ("White oxford shirt", "shirts", "white", 4, "smart-casual", ["work", "college", "date"], ["spring", "autumn"], "solid"),
    ("Light blue dress shirt", "shirts", "light blue", 4, "classic", ["work", "formal"], ["spring", "summer"], "solid"),
    ("Black cotton tee", "tshirts", "black", 2, "casual", ["casual", "college", "travel"], ["summer", "spring"], "solid"),
    ("Olive tee", "tshirts", "olive", 2, "casual", ["casual", "travel"], ["summer", "autumn"], "solid"),
    ("Cream tee", "tshirts", "cream", 2, "minimalist", ["casual", "college"], ["summer", "spring"], "solid"),
    ("Burgundy blouse", "tops_blouses", "burgundy", 3, "classic", ["work", "party", "date"], ["autumn", "winter"], "solid"),
    ("Grey trousers", "pants", "grey", 4, "classic", ["work", "formal"], ["autumn", "winter", "spring"], "solid"),
    ("Navy chinos", "pants", "navy", 3, "smart-casual", ["work", "college", "date"], ["spring", "autumn"], "solid"),
    ("Beige chinos", "pants", "beige", 3, "smart-casual", ["casual", "work", "travel"], ["spring", "summer"], "solid"),
    ("Dark denim jeans", "jeans_shorts", "denim", 2, "casual", ["casual", "college", "party"], ["autumn", "winter", "spring"], "solid"),
    ("Khaki shorts", "jeans_shorts", "khaki", 2, "casual", ["casual", "travel"], ["summer"], "solid"),
    ("Black midi dress", "dresses", "black", 4, "classic", ["party", "date", "formal"], ["spring", "autumn", "winter"], "solid"),
    ("White sneakers", "shoes", "white", 2, "casual", ["casual", "college", "travel"], ["spring", "summer", "autumn"], "solid"),
    ("Brown leather shoes", "shoes", "brown", 4, "classic", ["work", "formal", "date"], ["autumn", "winter", "spring"], "solid"),
    ("Black loafers", "shoes", "black", 4, "classic", ["work", "party", "formal"], ["spring", "autumn", "winter"], "solid"),
    ("Tan tote bag", "bags", "tan", 3, "minimalist", ["work", "college", "casual"], [], "solid"),
    ("Silver watch", "watches", "silver", 3, "classic", ["work", "party", "formal"], [], "solid"),
    ("Brown leather belt", "belts", "brown", 3, "classic", ["work", "casual"], [], "solid"),
    ("Black sunglasses", "sunglasses", "black", 2, "casual", ["casual", "travel"], ["summer"], "solid"),
]
SHAPES = {"shirts": "top", "tshirts": "top", "tops_blouses": "top", "pants": "pants", "jeans_shorts": "pants",
          "dresses": "dress", "shoes": "shoe", "bags": "bag", "watches": "watch", "belts": "belt", "sunglasses": "glasses"}

K = 2                      # supersampling factor: draw large, shrink for smooth edges
OUT = 800


def _P(pts):
    return [(x * K, y * K) for x, y in pts]


def _shade(rgb, f):
    return tuple(max(0, min(255, int(v * f))) for v in rgb)


def _shape_mask(shape, size):
    """Silhouette in 600-space, drawn white on black."""
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    if shape == "top":
        d.polygon(_P([(190, 110), (260, 88), (340, 88), (410, 110), (505, 215), (440, 262), (410, 226), (410, 505), (190, 505), (190, 226), (160, 262), (95, 215)]), fill=255)
    elif shape == "pants":
        d.polygon(_P([(185, 85), (415, 85), (440, 515), (332, 515), (300, 240), (268, 515), (160, 515)]), fill=255)
    elif shape == "dress":
        d.polygon(_P([(238, 78), (362, 78), (372, 215), (478, 525), (122, 525), (228, 215)]), fill=255)
    elif shape == "shoe":
        d.polygon(_P([(88, 405), (88, 352), (150, 330), (235, 300), (300, 250), (350, 212), (420, 205), (478, 222), (505, 290), (508, 405)]), fill=255)
        d.rounded_rectangle(_P([(88, 396), (508, 446)]), 22 * K, fill=255)
    elif shape == "bag":
        d.rounded_rectangle(_P([(120, 225), (480, 490)]), 34 * K, fill=255)
    elif shape == "watch":
        d.rectangle(_P([(262, 60), (338, 540)]), fill=255)
        d.ellipse(_P([(185, 205), (415, 435)]), fill=255)
    elif shape == "belt":
        d.rounded_rectangle(_P([(50, 268), (550, 332)]), 14 * K, fill=255)
    else:
        d.ellipse(_P([(85, 225), (295, 375)]), fill=255)
        d.ellipse(_P([(305, 225), (515, 375)]), fill=255)
        d.rectangle(_P([(285, 270), (315, 290)]), fill=255)
    if shape not in ("watch", "belt", "pants"):          # round the corners a little so garments look soft, not clip-art
        m = m.filter(ImageFilter.GaussianBlur(3 * K)).point(lambda v: 255 if v > 128 else 0).filter(ImageFilter.GaussianBlur(0.8))
    return m


def _details(shape, d, edge, light, cat):
    w = max(2, K * 2)
    L = lambda pts, c=edge, ww=w: d.line(_P(pts), fill=c, width=ww)
    if shape == "top":
        d.ellipse(_P([(262, 80), (338, 140)]), fill=_shade(edge, 0.85))                       # neckline
        L([(190, 226), (190, 505)]); L([(410, 226), (410, 505)]); L([(190, 495), (410, 495)], edge, w * 2)
        L([(190, 226), (160, 262)]); L([(410, 226), (440, 262)])
        if cat in ("shirts", "tops_blouses"):
            L([(300, 140), (300, 500)])
            for y in range(165, 480, 55):
                d.ellipse(_P([(294, y), (306, y + 12)]), fill=light, outline=edge)
            d.polygon(_P([(262, 88), (300, 142), (338, 88), (322, 84), (300, 112), (278, 84)]), fill=light, outline=edge)   # collar
    elif shape == "pants":
        L([(185, 100), (415, 100)], edge, w * 3); L([(300, 100), (300, 240)]); L([(300, 120), (332, 150), (332, 210)], edge, w)
        L([(215, 520), (300, 250)], _shade(edge, 1.1), w); L([(385, 520), (300, 250)], _shade(edge, 1.1), w)
        d.ellipse(_P([(292, 100), (308, 116)]), fill=light, outline=edge)
    elif shape == "dress":
        L([(228, 215), (372, 215)], edge, w * 2); d.ellipse(_P([(262, 70), (338, 128)]), fill=_shade(edge, 0.85))
        L([(300, 215), (300, 520)], _shade(edge, 1.15), w)
    elif shape == "shoe":
        d.rounded_rectangle(_P([(88, 404), (508, 446)]), 18 * K, fill=_shade(edge, 0.7) if sum(light) < 600 else (236, 231, 221))   # sole
        d.polygon(_P([(235, 300), (300, 250), (350, 212), (380, 215), (330, 290), (270, 330)]), fill=_shade(edge, 0.9))                # tongue shadow
        for i, (x, y) in enumerate([(250, 312), (282, 288), (314, 262), (346, 236)]):
            L([(x, y), (x + 34, y + 20)], light, w * 2)
        L([(150, 330), (235, 300)], edge); L([(420, 205), (470, 260), (480, 400)], edge)
    elif shape == "bag":
        d.arc(_P([(205, 100), (395, 330)]), 180, 360, fill=edge, width=K * 14)
        d.polygon(_P([(120, 225), (480, 225), (470, 320), (300, 355), (130, 320)]), outline=edge, width=w)
        d.rounded_rectangle(_P([(282, 332), (318, 366)]), 6 * K, fill=(200, 170, 90), outline=edge)
        L([(135, 480), (465, 480)], light, w)
    elif shape == "watch":
        d.ellipse(_P([(205, 225), (395, 415)]), fill=(244, 240, 230), outline=edge, width=K * 6)
        for a in range(12):
            import math
            x, y = 300 + 80 * math.sin(a * math.pi / 6), 320 - 80 * math.cos(a * math.pi / 6)
            d.ellipse(_P([(x - 3, y - 3), (x + 3, y + 3)]), fill=(40, 40, 40))
        L([(300, 320), (300, 262)], (30, 30, 30), K * 5); L([(300, 320), (345, 332)], (30, 30, 30), K * 4)
        for y in (120, 150, 450, 480):
            d.ellipse(_P([(296, y), (304, y + 8)]), fill=_shade(edge, 0.6))
    elif shape == "belt":
        d.rounded_rectangle(_P([(250, 250), (350, 350)]), 10 * K, outline=(205, 178, 100), width=K * 12)
        d.rectangle(_P([(296, 262), (304, 338)]), fill=(205, 178, 100))
        for x in range(380, 540, 32):
            d.ellipse(_P([(x, 296), (x + 8, 304)]), fill=_shade(edge, 0.7))
        L([(60, 276), (240, 276)], light, w); L([(60, 324), (240, 324)], light, w)
    else:
        d.ellipse(_P([(105, 245), (275, 355)]), fill=_shade(edge, 0.55)); d.ellipse(_P([(325, 245), (495, 355)]), fill=_shade(edge, 0.55))


def _draw(shape, rgb, label, cat=""):
    S = 600 * K
    # soft studio backdrop
    glow = Image.radial_gradient("L").resize((S, S))
    bg = ImageOps.colorize(ImageOps.invert(glow), (252, 249, 242), (226, 218, 203))
    mask = _shape_mask(shape, S)
    # contact shadow
    small = mask.resize((S // 4, S // 4))
    sh = Image.new("L", small.size, 0)
    sh.paste(small, (0, 4 * K))
    sh = sh.filter(ImageFilter.GaussianBlur(4 * K)).resize((S, S), Image.BILINEAR).point(lambda v: int(v * 0.32))
    bg.paste((60, 48, 30), (0, 0), sh)
    # fabric: diagonal light falloff + fine grain
    grad = Image.linear_gradient("L").resize((S, S)).rotate(35, resample=Image.BICUBIC, expand=False)
    base = Image.composite(Image.new("RGB", (S, S), _shade(rgb, 1.14)), Image.new("RGB", (S, S), _shade(rgb, 0.80)), grad)
    grain = Image.effect_noise((S // 2, S // 2), 18).point(lambda v: 118 + (v - 128) // 6).resize((S, S), Image.BILINEAR)
    base = ImageChops.multiply(base, Image.merge("RGB", (grain, grain, grain)).point(lambda v: min(255, v * 2)))
    edge, light = _shade(rgb, 0.55), _shade(rgb, 1.25)
    layer = base.copy()
    _details(shape, ImageDraw.Draw(layer), edge, light, cat)
    outline = mask.filter(ImageFilter.MaxFilter(3 * K | 1)).point(lambda v: 255 if v else 0)
    ring = ImageChops.subtract(outline, mask)
    bg.paste(layer, (0, 0), mask)
    bg.paste(edge, (0, 0), ring.filter(ImageFilter.GaussianBlur(1)))
    im = bg.resize((OUT, OUT), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.load_default(size=15)
    except TypeError:
        font = ImageFont.load_default()
    d.text((22, OUT - 36), "DEMO · ILLUSTRATION", fill=(150, 140, 125), font=font)
    return im


def build_items():
    """Create demo images and return ItemIn-compatible dicts."""
    out = []
    for name, cat, color, form, style, occ, seasons, pattern in DEMO:
        fname = f"demo_{uuid.uuid4().hex[:12]}.jpg"
        _draw(SHAPES.get(cat, "other"), PALETTE[color], name, cat).save(media_dir() / fname, "JPEG", quality=90)
        out.append(dict(name=name, category=cat, image=fname, primary_color=color, formality=form, style=style,
                        occasions=occ, seasons=seasons, pattern=pattern, description="Demo item (generated illustration).",
                        favorite=name in ("Black midi dress", "White sneakers")))
    return out
