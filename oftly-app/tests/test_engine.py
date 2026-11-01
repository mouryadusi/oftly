from datetime import date
from app import engine

def it(i, slot, color, formality=3, **kw):
    return {"id": i, "slot": slot, "category": slot, "primary_color": color, "formality": formality, "status": "available", **kw}

CTX = {"recent_outfits": {}, "prefs": {}, "today": date(2026, 1, 1)}

def test_color_pairs():
    assert engine.color_pair("black", "white") > engine.color_pair("red", "red")
    assert engine.color_pair("navy", "red") > engine.color_pair("red", "red")
    assert engine.color_pair("blue", "orange") > engine.color_pair("red", "blue")   # complementary beats a clash
    assert engine.color_pair("", "red") == 0.6

def test_neutral_outfit_beats_clashing():
    neutral = [it(1, "top", "white"), it(2, "bottom", "navy"), it(3, "shoes", "brown")]
    clash = [it(1, "top", "red"), it(2, "bottom", "purple"), it(3, "shoes", "yellow")]
    assert engine.score_outfit(neutral, CTX)["score"] > engine.score_outfit(clash, CTX)["score"]

def test_formality_consistency():
    even = [it(1, "top", "white", 4), it(2, "bottom", "grey", 4), it(3, "shoes", "black", 4)]
    mixed = [it(1, "top", "white", 5), it(2, "bottom", "grey", 1), it(3, "shoes", "black", 3)]
    assert engine.score_outfit(even, CTX)["breakdown"]["formality"] > engine.score_outfit(mixed, CTX)["breakdown"]["formality"]

def test_occasion_and_season_influence():
    a = [it(1, "top", "white", occasions=["work"], seasons=["summer"]), it(2, "bottom", "navy", occasions=["work"], seasons=["summer"])]
    b = [it(3, "top", "white", occasions=["party"], seasons=["winter"]), it(4, "bottom", "navy", occasions=["party"], seasons=["winter"])]
    ctx = {**CTX, "occasion": "work", "season": "summer"}
    assert engine.score_outfit(a, ctx)["score"] > engine.score_outfit(b, ctx)["score"]

def test_recent_repeat_penalised_and_pattern_penalty():
    o = [it(1, "top", "white"), it(2, "bottom", "navy")]
    base = engine.score_outfit(o, CTX)["score"]
    assert engine.score_outfit(o, {**CTX, "recent_outfits": {engine.signature([1, 2]): 2}})["score"] < base
    p = [it(1, "top", "white", pattern="striped"), it(2, "bottom", "navy", pattern="checked")]
    assert engine.color_score(p) < engine.color_score(o)

def test_generate_incomplete_and_small():
    out, msg = engine.generate([it(1, "top", "white")], CTX)
    assert out == [] and "shoes" in msg
    out, msg = engine.generate([it(1, "top", "white"), it(2, "bottom", "navy"), it(3, "shoes", "black")], CTX, count=3)
    assert len(out) == 1 and "Only 1" in msg
