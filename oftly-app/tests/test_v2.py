import json
import pytest
from app import intelligence, weather
from app.intelligence import http_provider
from conftest import add

def fake_om(temp=5.0, rain=70, hum_hours=None, calls=None):
    def _get(url, params):
        if calls is not None: calls.append((url, dict(params)))
        if "geocoding" in url:
            return {"results": [{"name": params["name"].title(), "country": "X", "latitude": 1, "longitude": 2}]}
        d = params["forecast_days"] - 1
        n = d + 1
        return {"current": {"temperature_2m": temp, "relative_humidity_2m": 80, "wind_speed_10m": 35, "is_day": 1, "time": "2026-10-23T12:00"},
                "daily": {"temperature_2m_max": [temp + 2] * n, "temperature_2m_min": [temp - 2] * n, "precipitation_probability_max": [rain] * n, "wind_speed_10m_max": [41] * n},
                "hourly": {"relative_humidity_2m": hum_hours or [60] * 24 * n}}
    return _get

@pytest.fixture(autouse=True)
def _clean():
    weather._cache.clear(); intelligence.reset()
    yield
    intelligence.reset()

def wardrobe(client, **tags):
    add(client, "Wool-look cold top", "shirts", primary_color="navy", seasons=["winter"])
    add(client, "Light summer top", "shirts", primary_color="white", seasons=["summer"])
    add(client, "Grey trousers", "pants", primary_color="grey", seasons=["winter", "summer"])
    add(client, "Brown shoes", "shoes", primary_color="brown")

def weather_on(client, city="Home"):
    assert client.put("/api/preferences", json={"city": city, "use_weather": True}).status_code == 200

# ---------- destination weather ----------
def test_destination_weather_day_and_humidity(client, monkeypatch):
    calls = []; monkeypatch.setattr(weather, "_get", fake_om(temp=20, calls=calls, hum_hours=[50] * 24 + [70] * 24 + [90] * 24))
    weather_on(client)
    w = client.get("/api/weather?destination=paris&day=2").json()
    assert w["available"] and w["city"] == "Paris" and w["day"] == 2 and w["temp_c"] == 20.0     # (22+18)/2
    assert w["humidity"] == 90 and w["wind_kph"] == 41 and w["rain_chance"] == 70 and w["band"] == "spring"
    assert calls[1][1]["forecast_days"] == 3
    assert client.get("/api/weather?day=9").status_code == 422

def test_weather_requires_opt_in_and_place(client, monkeypatch):
    monkeypatch.setattr(weather, "_get", lambda *a: pytest.fail("network must not be touched"))
    off = client.get("/api/weather?destination=Paris").json()
    assert off["available"] is False and off["off"] is True
    client.put("/api/preferences", json={"use_weather": True})
    assert client.get("/api/weather").json()["available"] is False          # no destination and no home city

def test_place_name_validation(client, monkeypatch):
    monkeypatch.setattr(weather, "_get", lambda *a: pytest.fail("must not call out"))
    assert weather.lookup("<script>alert(1)</script>")["available"] is False
    assert weather.lookup("a" * 200)["available"] is False

def test_destination_climate_changes_the_outfit(client, monkeypatch):
    wardrobe(client); weather_on(client)
    monkeypatch.setattr(weather, "_get", fake_om(temp=2))
    cold = client.get("/api/outfits/generate?destination=Oslo&count=2&seed=1").json()
    assert cold["weather"]["available"] and cold["destination"] == "Oslo"
    first = cold["outfits"][0]
    assert "Wool-look cold top" in [i["name"] for i in first["items"]]
    assert any("Oslo" in p and "2°C" in p and "cold" in p for p in first["style"]["practical"])
    assert any("Rain is likely" in p for p in first["style"]["practical"]) and any("Humid" in p for p in first["style"]["practical"]) and any("Windy" in p for p in first["style"]["practical"])
    weather._cache.clear(); monkeypatch.setattr(weather, "_get", fake_om(temp=33, rain=0))
    hot = client.get("/api/outfits/generate?destination=Dubai&count=2&seed=1").json()["outfits"][0]
    assert "Light summer top" in [i["name"] for i in hot["items"]]

def test_weather_failure_degrades_gracefully(client, monkeypatch):
    wardrobe(client); weather_on(client)
    def boom(*a, **k): raise OSError("offline")
    monkeypatch.setattr(weather, "_get", boom)
    r = client.get("/api/outfits/generate?destination=Nowhere").json()
    assert r["outfits"] and r["weather"]["available"] is False and "unreachable" in r["weather"]["reason"]
    assert "No weather was used" in r["outfits"][0]["style"]["practical"][0]        # nothing invented

def test_season_is_not_used_when_destination_weather_exists(client, monkeypatch):
    wardrobe(client); weather_on(client); monkeypatch.setattr(weather, "_get", fake_om(temp=2))
    a = client.get("/api/outfits/generate?destination=Oslo&count=1&seed=3").json()["outfits"][0]["score"]
    b = client.get("/api/outfits/generate?destination=Oslo&season=summer&count=1&seed=3").json()["outfits"][0]["score"]
    assert a == b

# ---------- local-API security ----------
def test_dns_rebinding_host_is_rejected(client):
    assert client.get("/api/health", headers={"host": "evil.example"}).status_code == 400
    assert client.get("/api/health", headers={"host": "127.0.0.1:8000"}).status_code == 200
    assert client.get("/api/health", headers={"host": "localhost:8000"}).status_code == 200

def test_cross_site_writes_are_refused(client):
    body = {"name": "x", "category": "shirts"}
    assert client.post("/api/items", json=body, headers={"origin": "https://evil.example"}).status_code == 403
    assert client.post("/api/items", json=body, headers={"origin": "null"}).status_code == 403
    assert client.post("/api/items", json=body, headers={"origin": "http://testserver"}).status_code == 201
    assert client.delete("/api/data?confirm=true", headers={"origin": "http://127.0.0.1:9999"}).status_code == 403
    assert client.get("/api/items", headers={"origin": "https://evil.example"}).status_code == 200      # reads carry no CORS grant

def test_security_headers(client):
    h = client.get("/api/health").headers
    assert "frame-ancestors 'none'" in h["content-security-policy"] and "script-src 'self'" in h["content-security-policy"]
    assert h["x-content-type-options"] == "nosniff" and h["referrer-policy"] == "no-referrer" and h["cache-control"] == "no-store"
    assert "access-control-allow-origin" not in h

# ---------- insights and one-click filters ----------
def test_insights_and_filters(client):
    a = add(client, "Navy tee", "tshirts", primary_color="navy", price=300.0)
    b = add(client, "Red dress", "dresses", primary_color="red", price=1000.0)
    add(client, "Brown shoes", "shoes", primary_color="brown")
    o = client.post("/api/outfits", json={"item_ids": [a["id"], b["id"]]}).json()["id"]
    for _ in range(3): client.post(f"/api/outfits/{o}/wear")
    i = client.get("/api/insights").json()
    assert i["total"] == 3 and i["worn_30d"] == 2 and i["never_worn"] == 1 and i["dormant_60d"] == 1
    assert i["neutral_share"] == 0.67 and sum(i["wears_by_week"]) == 3 and i["wears_by_week"][-1] == 3
    assert i["cost_per_wear"][0]["name"] == "Navy tee" and i["cost_per_wear"][0]["per_wear"] == 100.0
    names = lambda q: sorted(x["name"] for x in client.get("/api/items?" + q).json()["items"])
    assert names("unworn_days=30") == ["Brown shoes"]
    assert names("palette=neutral") == ["Brown shoes", "Navy tee"] and names("palette=colour") == ["Red dress"]
    assert client.get("/api/items?palette=nope").status_code == 422

def test_empty_wardrobe_insights(client):
    i = client.get("/api/insights").json()
    assert i["total"] == 0 and i["neutral_share"] is None and i["cost_per_wear"] == [] and i["wears_by_week"] == [0] * 8

# ---------- intelligence boundary ----------
class R:
    def __init__(self, data): self._d, self.content = data, json.dumps(data).encode()
    def json(self): return self._d
    def raise_for_status(self): pass

def use_provider(monkeypatch, handler, url="http://127.0.0.1:9911"):
    monkeypatch.setenv("OFTLY_INTELLIGENCE_URL", url); intelligence.reset()
    monkeypatch.setattr(http_provider.httpx, "request", lambda method, u, **kw: handler(method, u, kw))

def test_default_is_null_provider_and_app_unchanged(client):
    s = client.get("/api/intelligence/status").json()
    assert s["enabled"] is False and s["contract"] == "oftly.intelligence/1"

@pytest.mark.parametrize("bad", ["http://example.com:80", "https://127.0.0.1", "http://10.0.0.5:9", "http://user:pw@127.0.0.1:9", "ftp://localhost", "http://127.0.0.1.evil.com"])
def test_non_loopback_urls_are_refused(monkeypatch, bad):
    with pytest.raises(intelligence.UnsafeURL): http_provider.HttpProvider(bad)
    monkeypatch.setenv("OFTLY_INTELLIGENCE_URL", bad); intelligence.reset()
    assert intelligence.get_provider().name == "none"

def test_provider_nudges_scores_within_bounds_and_is_reported(client, monkeypatch):
    wardrobe(client)
    seen = {}
    def handler(method, url, kw):
        if url.endswith("/v1/rank_outfits"):
            body = kw["json"]; seen["body"] = body
            return R({"adjustments": [{"id": o["id"], "delta": 4.0, "note": "Echoes a look you wore"} for o in body["outfits"]] + [{"id": "zz", "delta": 3}, {"id": body["outfits"][0]["id"], "delta": 99}]})
        return R({"capabilities": ["rank_outfits"]})
    base = client.get("/api/outfits/generate?count=1&seed=2").json()["outfits"][0]["score"]
    use_provider(monkeypatch, handler)
    o = client.get("/api/outfits/generate?count=1&seed=2").json()["outfits"][0]
    assert o["adjustments"]["intelligence"] == 4.0 and abs(o["score"] - min(100, base + 4)) < 0.11
    assert any(l.startswith("OFTLY Intelligence:") for l in o["style"]["why_for_you"])
    p = seen["body"]["outfits"][0]["pieces"][0]
    assert set(p) == {"id", "slot", "category", "colour", "pattern", "style", "formality"}        # no names, photos or notes cross the boundary
    assert seen["body"]["contract"] == "oftly.intelligence/1"

def test_broken_provider_never_breaks_the_app(client, monkeypatch):
    wardrobe(client)
    def handler(method, url, kw): raise OSError("down")
    use_provider(monkeypatch, handler)
    for _ in range(5):
        r = client.get("/api/outfits/generate?count=1")
        assert r.status_code == 200 and r.json()["outfits"]
    st = client.get("/api/intelligence/status").json()
    assert st["enabled"] and st["reachable"] is False and st["breaker_open"] is True       # stops calling a dead service
    def junk(method, url, kw): return R({"adjustments": "nope"})
    use_provider(monkeypatch, junk)
    assert client.get("/api/outfits/generate?count=1").json()["outfits"]

def test_suggestions_are_separate_from_confirmed_data(client, monkeypatch, tmp_path):
    up = client.post("/api/uploads", files={"file": ("a.png", __import__("conftest").png(), "image/png")}).json()
    it = add(client, "Photo item", "shirts", image=up["image"])
    monkeypatch.setenv("OFTLY_INTELLIGENCE_URL", "http://localhost:9911"); intelligence.reset()
    monkeypatch.setattr(http_provider.httpx, "request", lambda m, u, **kw: R({"suggestions": [{"field": "category", "value": "jeans_shorts", "confidence": 0.9}, {"field": "x", "value": "y", "confidence": 7}]}))
    r = client.get(f"/api/items/{it['id']}/suggestions").json()
    assert r["confirmed"] is False and r["suggestions"] == [{"field": "category", "value": "jeans_shorts", "confidence": 0.9}]     # invalid entry dropped
    assert client.get(f"/api/items/{it['id']}").json()["category"] == "shirts"                       # never auto-applied

def test_uploaded_photos_lose_exif_and_gps(client):
    import io
    from PIL import Image
    im = Image.new("RGB", (64, 64), (200, 100, 50))
    exif = Image.Exif(); exif[0x010F] = "SecretCam"; exif[0x8825] = {1: "N", 2: (16.0, 30.0, 0.0), 3: "E", 4: (80.0, 37.0, 0.0)}   # make + GPS
    buf = io.BytesIO(); im.save(buf, "JPEG", exif=exif); assert b"SecretCam" in buf.getvalue()
    r = client.post("/api/uploads", files={"file": ("p.jpg", buf.getvalue(), "image/jpeg")}); assert r.status_code in (200, 201), r.text
    raw = client.get(r.json()["image_url"]).content
    assert b"SecretCam" not in raw and b"Exif" not in raw
    assert not Image.open(io.BytesIO(raw)).getexif()
