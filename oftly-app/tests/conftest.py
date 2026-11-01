import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient

PASSWORD = "correct-horse-battery-7"


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Every test gets its own empty data directory and clean limiter/outbox. Demo fixtures are enabled for tests only."""
    monkeypatch.setenv("OFTLY_DATA", str(tmp_path))
    monkeypatch.setenv("OFTLY_MAIL", "memory")
    monkeypatch.setenv("OFTLY_ENABLE_DEMO", "1")
    monkeypatch.delenv("OFTLY_INVITE_CODES", raising=False)
    from app import auth, db
    auth.limiter.clear(); auth.OUTBOX.clear(); auth._init_done.clear(); db._ready.clear()


def signed_in(email="tester@example.com", name="Tester"):
    """A TestClient registered and signed in as its own account (separate cookie jar), with the CSRF header set like the web UI does."""
    from app.main import app
    c = TestClient(app).__enter__()
    r = c.post("/api/auth/register", json={"email": email, "password": PASSWORD, "display_name": name})
    assert r.status_code == 201, r.text
    c.headers["x-csrf-token"] = c.cookies.get("oftly_csrf")
    return c


@pytest.fixture()
def client():
    return signed_in()


@pytest.fixture()
def second_client():
    return signed_in("friend@example.com", "Friend")


@pytest.fixture()
def anon():
    from app.main import app
    return TestClient(app).__enter__()


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
