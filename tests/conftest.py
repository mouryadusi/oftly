import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VEYA_DATA", str(tmp_path))
    from app import db
    from app.main import app
    db.init_db()
    return TestClient(app)

def png(color=(200, 30, 30), size=(80, 60)):
    b = io.BytesIO()
    Image.new("RGB", size, color).save(b, "PNG")
    return b.getvalue()

def add(client, name="Item", category="shirts", **kw):
    r = client.post("/api/items", json={"name": name, "category": category, **kw})
    assert r.status_code == 201, r.text
    return r.json()

def basic_wardrobe(client):
    return [add(client, "White shirt", "shirts", primary_color="white", formality=4),
            add(client, "Navy chinos", "pants", primary_color="navy", formality=3),
            add(client, "Brown shoes", "shoes", primary_color="brown", formality=4),
            add(client, "Black tee", "tshirts", primary_color="black", formality=2),
            add(client, "Denim jeans", "jeans_shorts", primary_color="denim", formality=2),
            add(client, "White sneakers", "shoes", primary_color="white", formality=2)]
