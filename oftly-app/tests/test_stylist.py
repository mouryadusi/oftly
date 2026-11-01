import re
from datetime import date
import pytest
from app import engine, stylist, weather
from conftest import add

def it(i, slot, name, color, formality=3, **kw):
    return {"id": i, "slot": slot, "category": slot, "category_label": slot.capitalize(), "name": name, "primary_color": color,
            "formality": formality, "status": "available", **kw}

CTX = {"recent_outfits": {}, "prefs": {}, "today": date(2026, 1, 20)}
FORBIDDEN = re.compile(r"cotton|linen|wool|silk|leather|cashmere|denim fabric|breathable fabric|cosy|cozy|insulat|stretch|slim fit|oversized", re.I)

def narrate(items, **ctx):
    c = {**CTX, **ctx}
    return engine.build(items, c, describe=True)

def grounded_text(s):
    return " ".join([s["intention"], s["colour_story"], s["focal_point"]["text"], *s["why_for_you"], *[p["note"] for p in s["pieces"]]])

OUTFIT_A = [it(1, "top", "Ivory shell top", "cream"), it(2, "bottom", "Champagne trousers", "beige"), it(3, "shoes", "Tan loafers", "tan")]
OUTFIT_B = [it(4, "top", "Rust knit", "orange", pattern="striped"), it(5, "bottom", "Black jeans", "black"), it(6, "shoes", "White trainers", "white")]

def test_description_is_grounded_and_has_all_sections():
    s = narrate(OUTFIT_A, occasion="work")["style"]
    assert s["title"] and s["intention"] and s["colour_story"] and s["practical"] and s["why_for_you"] and s["factors"]
    assert [p["id"] for p in s["pieces"]] == [1, 2, 3] and all(p["note"] for p in s["pieces"])
    assert not FORBIDDEN.search(grounded_text(s))
    assert "fabric, warmth and breathability" in s["not_assessed"]      # honesty about what is not known

def test_only_colours_present_are_mentioned():
    all_colours = {"cream", "beige", "tan", "orange", "black", "white", "red", "green", "blue", "navy", "grey", "brown", "pink", "gold", "ivory", "champagne"}
    s = narrate(OUTFIT_A)["style"]
    text = (s["colour_story"] + " " + s["focal_point"]["text"]).lower()
    present = {"cream", "beige", "tan"}
    assert {c for c in all_colours if re.search(rf"\b{c}\b", text)} <= present   # no ivory/champagne invented from item names

def test_different_outfits_get_different_descriptions():
    a, b = narrate(OUTFIT_A)["style"], narrate(OUTFIT_B)["style"]
    assert a["title"] != b["title"] and a["summary"] != b["summary"]
    assert "orange" in b["focal_point"]["text"] and "Rust knit" in b["focal_point"]["text"]
    assert a["focal_point"]["item_id"] is None                      # all-neutral, plain: honestly no focal piece

def test_titles_unique_within_a_batch():
    twin = [it(7, "top", "Cream tee", "cream"), it(8, "bottom", "Beige chinos", "beige"), it(9, "shoes", "Tan boots", "tan")]
    outs = [engine.build(OUTFIT_A, CTX), engine.build(twin, CTX)]
    stylist.describe_all(outs, CTX)
    assert outs[0]["style"]["title"] != outs[1]["style"]["title"]

def test_why_for_you_uses_real_preferences_and_history():
    prefs = {"favorite_colors": ["orange"], "preferred_styles": ["casual"], "disliked_colors": []}
    items = [{**OUTFIT_B[0], "favorite": True, "style": "casual", "last_worn": "2025-12-01"}, *OUTFIT_B[1:]]
    w = " ".join(narrate(items, prefs=prefs)["style"]["why_for_you"])
    assert "Favourite colour orange shows up" in w and "Style preference" in w and "Rust knit" in w and "50 days ago" in w
    empty = narrate(OUTFIT_B)["style"]["why_for_you"]
    assert "doesn't know enough" in empty[0]                         # no invented personalisation

def test_practical_uses_weather_only_when_supplied():
    assert "No weather was used" in narrate(OUTFIT_A)["style"]["practical"][0]
    wx = {"temp_c": 8, "rain_chance": 70}
    p = " ".join(narrate(OUTFIT_A, weather=wx)["style"]["practical"])
    assert "8°C" in p and "Rain is likely (70%)" in p and "check Tan loafers" in p and "can't tell how warm" in p

def test_single_rejection_is_gentle_and_expires():
    rej, aff = engine.learn([("1-2-3", "reject", 1)])
    assert "1-2-3" in rej and -0.5 < aff[1] < 0
    rej, aff = engine.learn([("1-2-3", "reject", 20)])
    assert rej == set()                                              # exact combination allowed again after 14 days
    _, one = engine.learn([("1-2-3", "reject", 1)])
    _, three = engine.learn([("1-2-3", "reject", 1), ("1-4-5", "reject", 2), ("1-6-7", "reject", 3)])
    assert three[1] < one[1] < 0 and three[1] > -1.01                 # repeated rejections of one item accumulate, bounded
    _, aff_old = engine.learn([("1-2", "reject", 1)]); _, aff_older = engine.learn([("1-2", "reject", 90)])
    assert abs(aff_older[1]) < abs(aff_old[1])                       # fades with time

def test_learned_affinity_and_dislikes_adjust_score_transparently():
    base = engine.score_outfit(OUTFIT_B, CTX)
    liked = engine.score_outfit(OUTFIT_B, {**CTX, "affinity": {4: 1.0, 5: 1.0, 6: 1.0}})
    assert liked["score"] > base["score"] and liked["adjustments"]["learned"] > 0
    avoid = engine.score_outfit(OUTFIT_B, {**CTX, "prefs": {"disliked_colors": ["orange"]}})
    assert avoid["score"] < base["score"] and avoid["adjustments"]["avoided_colour"] < 0

def test_weather_failure_never_fabricates(monkeypatch):
    weather._cache.clear()
    def boom(*a, **k): raise OSError("offline")
    monkeypatch.setattr(weather, "_get", boom)
    assert weather.lookup("Nowhere") == {"available": False, "reason": "Weather service unreachable."}

def test_weather_parsing(monkeypatch):
    weather._cache.clear()
    def fake(url, params):
        if "geocoding" in url: return {"results": [{"name": "Vijayawada", "country": "India", "latitude": 16.5, "longitude": 80.6}]}
        return {"current": {"temperature_2m": 31.2, "relative_humidity_2m": 60, "wind_speed_10m": 9, "is_day": 1, "time": "2026-10-22T12:00"},
                "daily": {"precipitation_probability_max": [40]}}
    monkeypatch.setattr(weather, "_get", fake)
    w = weather.lookup("Vijayawada")
    assert w["available"] and w["temp_c"] == 31.2 and w["rain_chance"] == 40 and w["source"] == "Open-Meteo"

# ---- API level ----
def wardrobe(client):
    for n, c, col in [("White shirt", "shirts", "white"), ("Navy chinos", "pants", "navy"), ("Brown shoes", "shoes", "brown"),
                      ("Red tee", "tshirts", "red"), ("Denim jeans", "jeans_shorts", "denim"), ("White sneakers", "shoes", "white")]:
        add(client, n, c, primary_color=col)

def test_generate_returns_styled_outfits(client):
    wardrobe(client)
    outs = client.get("/api/outfits/generate?count=3").json()["outfits"]
    assert outs and all(o["style"]["title"] and o["style"]["pieces"] for o in outs)
    assert len({o["style"]["summary"] for o in outs}) == len(outs)
    assert "Colours work together" not in outs[0]["reason"]

def test_profile_roundtrip_and_validation(client):
    r = client.put("/api/preferences", json={"preferred_name": "Mourya", "gender": "prefer-not-to-say", "city": "Vijayawada",
                                              "use_weather": True, "fit": "relaxed", "disliked_colors": ["yellow"]})
    assert r.status_code == 200 and client.get("/api/preferences").json()["preferred_name"] == "Mourya"
    for bad in [{"gender": "x"}, {"preferred_name": "a" * 200}, {"use_weather": "yes"}, {"disliked_colors": [1]}, {"nope": 1}]:
        assert client.put("/api/preferences", json=bad).status_code == 422, bad

def test_weather_off_by_default_and_opt_in(client, monkeypatch):
    weather._cache.clear()
    assert client.get("/api/weather").json()["available"] is False
    monkeypatch.setattr(weather, "_get", lambda u, p: {"results": [{"name": "X", "latitude": 1, "longitude": 1}]} if "geocoding" in u else
                        {"current": {"temperature_2m": 8.0}, "daily": {"precipitation_probability_max": [80]}})
    client.put("/api/preferences", json={"city": "X", "use_weather": True})
    assert client.get("/api/weather").json()["temp_c"] == 8.0
    wardrobe(client)
    first = client.get("/api/outfits/generate?count=1").json()["outfits"][0]
    assert any("8°C" in p for p in first["style"]["practical"])

def test_wearing_an_outfit_feeds_learning(client):
    wardrobe(client)
    o = client.get("/api/outfits/generate?count=1").json()["outfits"][0]
    oid = client.post("/api/outfits", json={"item_ids": o["item_ids"], "name": o["style"]["title"], "reason": o["reason"]}).json()["id"]
    assert client.post(f"/api/outfits/{oid}/wear").status_code == 201
    assert client.post("/api/feedback", json={"item_ids": o["item_ids"], "action": "like"}).status_code == 201
    again = client.post("/api/outfits/evaluate", json={"item_ids": o["item_ids"]}).json()
    assert again["adjustments"].get("learned", 0) > 0 and again["style"]["title"]

def test_metal_accessories_are_a_finish_not_an_accent_colour():
    items = [*OUTFIT_A, it(10, "accessory", "Gold chain", "gold")]
    s = narrate(items)["style"]
    assert s["focal_point"]["item_id"] is None and "restrained gold finish" in s["colour_story"]
    assert "Gold" not in s["title"] and "only colour" not in s["colour_story"]

def test_title_and_grammar_follow_the_actual_palette():
    s = narrate([it(1, "top", "Cream tee", "cream"), it(2, "bottom", "Navy chinos", "navy"), it(3, "shoes", "Red shoes", "red")])["style"]
    assert "Red" in s["title"] and "keep everything else quiet" in s["colour_story"]
