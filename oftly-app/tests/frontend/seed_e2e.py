"""Creates the browser-test account + sample wardrobe in a data directory BEFORE the server starts (so the server itself can run with demos OFF,
exactly like production). Fixtures only: seeded@example.com / the password below. Usage: OFTLY_DATA=/tmp/x python seed_e2e.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
os.environ["OFTLY_ENABLE_DEMO"] = "1"         # seeding only; the test server is started without this
from fastapi.testclient import TestClient
from app.main import app

EMAIL, PASSWORD = "seeded@example.com", "correct-horse-battery-7"
with TestClient(app) as c:
    assert c.post("/api/auth/register", json={"email": EMAIL, "password": PASSWORD, "display_name": "Mourya"}).status_code == 201
    c.headers["x-csrf-token"] = c.cookies["oftly_csrf"]
    assert c.post("/api/demo").status_code == 201
    assert c.put("/api/preferences", json={"onboarded": True, "walkthrough_done": True, "preferred_name": "Mourya", "city": "Vijayawada",
                                           "use_weather": True, "favorite_colors": ["navy"], "disliked_colors": ["yellow"]}).status_code == 200
print("seeded", EMAIL)
