"""Original generated demo wardrobe: flat illustrations drawn with Pillow (no third-party images)."""
import uuid
from PIL import Image, ImageDraw, ImageFont
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

def _draw(shape, rgb, label):
    S = 600
    im = Image.new("RGB", (S, S), (246, 242, 234))
    d = ImageDraw.Draw(im)
    edge = tuple(max(0, v - 40) for v in rgb)
    if shape == "top":
        d.polygon([(190, 110), (260, 90), (340, 90), (410, 110), (500, 210), (440, 255), (410, 220), (410, 500), (190, 500), (190, 220), (160, 255), (100, 210)], fill=rgb, outline=edge)
    elif shape == "pants":
        d.polygon([(190, 90), (410, 90), (430, 510), (330, 510), (300, 230), (270, 510), (170, 510)], fill=rgb, outline=edge)
    elif shape == "dress":
        d.polygon([(240, 80), (360, 80), (380, 230), (470, 520), (130, 520), (220, 230)], fill=rgb, outline=edge)
    elif shape == "shoe":
        d.rounded_rectangle([110, 300, 500, 440], 50, fill=rgb, outline=edge)
        d.rectangle([110, 410, 500, 450], fill=edge)
    elif shape == "bag":
        d.arc([210, 110, 390, 300], 180, 360, fill=edge, width=14)
        d.rounded_rectangle([130, 230, 470, 480], 28, fill=rgb, outline=edge)
    elif shape == "watch":
        d.rectangle([265, 70, 335, 530], fill=edge)
        d.ellipse([190, 210, 410, 430], fill=rgb, outline=edge, width=8)
        d.line([300, 320, 300, 255], fill=(30, 30, 30), width=6)
        d.line([300, 320, 345, 320], fill=(30, 30, 30), width=6)
    elif shape == "belt":
        d.rectangle([60, 270, 540, 330], fill=rgb, outline=edge)
        d.rectangle([260, 255, 340, 345], outline=(180, 165, 120), width=10)
    else:
        d.ellipse([90, 230, 290, 370], fill=rgb, outline=edge)
        d.ellipse([310, 230, 510, 370], fill=rgb, outline=edge)
        d.line([290, 280, 310, 280], fill=edge, width=10)
    try:
        font = ImageFont.load_default(size=20)
    except TypeError:
        font = ImageFont.load_default()
    d.text((20, 568), "Demo item - illustration", fill=(140, 130, 115), font=font)
    return im

def build_items():
    """Create demo images and return ItemIn-compatible dicts."""
    out = []
    for name, cat, color, form, style, occ, seasons, pattern in DEMO:
        fname = f"demo_{uuid.uuid4().hex[:12]}.jpg"
        _draw(SHAPES.get(cat, "other"), PALETTE[color], name).save(media_dir() / fname, "JPEG", quality=88)
        out.append(dict(name=name, category=cat, image=fname, primary_color=color, formality=form, style=style,
                        occasions=occ, seasons=seasons, pattern=pattern, description="Demo item (generated illustration).",
                        favorite=name in ("Black midi dress", "White sneakers")))
    return out
