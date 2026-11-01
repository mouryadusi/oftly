"""Rule-based outfit engine. Pure functions over item dicts (no DB, no I/O).

Scoring is transparent: each component is 0..1 with a fixed weight; the weighted mean
becomes a 0-100 score and is returned with a per-component breakdown and reasons.
To plug in a local ML model later, add a component to `score_outfit` (see docs/ML_INTEGRATION.md).
"""
import itertools
import random
from datetime import date

SLOT_ORDER = ["top", "dress", "bottom", "shoes", "bag", "accessory"]
CORE = {"top", "bottom", "dress"}
NEUTRAL = {"black", "white", "grey", "gray", "beige", "cream", "navy", "brown", "khaki", "denim", "tan", "silver"}
HUE = {"red": 0, "burgundy": 350, "pink": 330, "orange": 30, "gold": 48, "yellow": 55, "olive": 75,
       "green": 120, "teal": 175, "light blue": 200, "blue": 220, "purple": 280, "maroon": 350, "mustard": 48}
OCC_FORMALITY = {"casual": 2, "college": 2, "travel": 2, "date": 3, "party": 3, "work": 4, "office": 4,
                 "formal": 5, "wedding": 5}
PLAIN = {"", "solid", "plain", "none"}
WEIGHTS = {"color": 40, "formality": 20, "occasion": 15, "season": 10, "preference": 10, "freshness": 5}

def norm(c):
    return (c or "").strip().lower()

def signature(ids):
    return "-".join(str(i) for i in sorted(ids))

def sort_items(items):
    return sorted(items, key=lambda i: (SLOT_ORDER.index(i["slot"]) if i.get("slot") in SLOT_ORDER else 9, i["id"]))

def color_pair(a, b):
    """Compatibility of two colour names, 0..1."""
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.6
    if a in NEUTRAL and b in NEUTRAL:
        return 0.7 if a == b else 0.92
    if a in NEUTRAL or b in NEUTRAL:
        return 0.85
    if a == b:
        return 0.65
    ha, hb = HUE.get(a), HUE.get(b)
    if ha is None or hb is None:
        return 0.5
    d = abs(ha - hb)
    d = min(d, 360 - d)
    if d <= 40:
        return 0.8      # analogous
    if d >= 150:
        return 0.72     # complementary
    return 0.5 if d >= 100 else 0.35

def color_score(items):
    cols = [(i, norm(i.get("primary_color"))) for i in items]
    tot = wsum = 0.0
    for (a, ca), (b, cb) in itertools.combinations(cols, 2):
        w = 1.0 if a["slot"] in CORE and b["slot"] in CORE else 0.5
        tot += w * color_pair(ca, cb)
        wsum += w
    s = tot / wsum if wsum else 0.6
    if sum(1 for i in items if norm(i.get("pattern")) not in PLAIN) >= 2:
        s -= 0.15      # two patterned pieces compete
    if len({c for _, c in cols if c and c not in NEUTRAL}) > 2:
        s -= 0.2       # too many accent colours
    return max(0.0, min(1.0, s))

def formality_score(items, target=None):
    f = [i.get("formality") or 3 for i in items]
    s = 1 - (max(f) - min(f)) / 4
    if target:
        s = 0.5 * s + 0.5 * (1 - abs(sum(f) / len(f) - target) / 4)
    return max(0.0, min(1.0, s))

def _match(items, key, want):
    if not want:
        return None
    vals = []
    for i in items:
        have = i.get(key) or []
        vals.append(0.5 if not have else 1.0 if (want in have or "all" in have) else 0.0)
    return sum(vals) / len(vals)

CLIMATE = ["winter", "autumn", "spring", "summer"]       # cold -> hot, same tags items already carry

def climate_fit(items, band):
    """1.0 if an item is tagged for the destination's temperature band, 0.6 for an adjacent band, 0 otherwise; untagged = 0.5."""
    k, out = CLIMATE.index(band), []
    for i in items:
        tags = i.get("seasons") or []
        if not tags:
            out.append(0.5)
        elif band in tags or "all" in tags:
            out.append(1.0)
        else:
            out.append(0.6 if any(t in CLIMATE and abs(CLIMATE.index(t) - k) == 1 for t in tags) else 0.0)
    return sum(out) / len(out)

def _fresh(i, today):
    lw = i.get("last_worn")
    return 1.0 if not lw else min((today - date.fromisoformat(lw)).days / 14, 1.0)

def score_outfit(items, ctx):
    items = sort_items(items)
    today = ctx.get("today") or date.today()
    occ = (ctx.get("occasion") or "").lower() or None
    season = (ctx.get("season") or "").lower() or None
    prefs = ctx.get("prefs") or {}
    fav_c = {x.lower() for x in prefs.get("favorite_colors", [])}
    fav_s = {x.lower() for x in prefs.get("preferred_styles", [])}
    parts = {"color": color_score(items),
             "formality": formality_score(items, OCC_FORMALITY.get(occ)),
             "freshness": sum(_fresh(i, today) for i in items) / len(items)}
    if (v := _match(items, "occasions", occ)) is not None:
        parts["occasion"] = v
    if ctx.get("climate"):
        parts["season"] = climate_fit(items, ctx["climate"])          # destination weather -> item climate tags
    elif (v := _match(items, "seasons", season)) is not None:         # legacy explicit season (API only; not in the UI)
        parts["season"] = v
    if fav_c or fav_s:
        flags = []
        for i in items:
            if fav_c:
                flags.append(norm(i.get("primary_color")) in fav_c)
            if fav_s:
                flags.append(norm(i.get("style")) in fav_s)
        parts["preference"] = sum(flags) / len(flags)
    total = sum(WEIGHTS[k] * v for k, v in parts.items()) / sum(WEIGHTS[k] for k in parts) * 100
    total += 3 * sum(1 for i in items if i.get("favorite")) / len(items)   # small favourites bonus
    ids = [i["id"] for i in items]
    if signature(ids) in ctx.get("recent_outfits", {}):
        total -= 15                                                       # worn in the last 14 days
    # Personal adjustments, reported separately so the score stays explainable.
    adjustments = {}
    dis = {x.lower() for x in prefs.get("disliked_colors", [])}
    n_dis = sum(1 for i in items if norm(i.get("primary_color")) in dis)
    if n_dis:
        adjustments["avoided_colour"] = -min(12.0, 6.0 * n_dis)
    aff = ctx.get("affinity") or {}
    learned = 6.0 * sum(aff.get(i["id"], 0.0) for i in items) / len(items)
    if abs(learned) >= 0.5:
        adjustments["learned"] = round(max(-6.0, min(6.0, learned)), 1)
    total += sum(adjustments.values())
    reasons = []
    names = list(dict.fromkeys(norm(i.get("primary_color")) for i in items if i.get("primary_color")))
    if parts["color"] >= 0.75 and names:
        reasons.append(f"Colours work together ({', '.join(names[:4])})")
    elif parts["color"] < 0.5:
        reasons.append("A bolder colour mix")
    if parts["formality"] >= 0.8:
        reasons.append("Consistent formality level")
    if parts.get("occasion", 0) >= 0.67:
        reasons.append(f"Suits {occ}")
    if parts.get("season", 0) >= 0.67:
        reasons.append(f"Right for {season}")
    if parts["freshness"] >= 0.9:
        reasons.append("Pieces you haven't worn lately")
    return {"score": round(max(0, min(100, total)), 1),
            "breakdown": {k: round(v * 100) for k, v in parts.items()}, "reasons": reasons,
            "adjustments": adjustments}

def build(items, ctx, describe=False):
    items = sort_items(items)
    s = score_outfit(items, ctx)
    ids = [i["id"] for i in items]
    o = {"item_ids": ids, "items": items, "signature": signature(ids), **s,
         "reason": "; ".join(s["reasons"]) or "A balanced combination"}
    if describe:
        from . import stylist          # lazy: stylist imports engine's constants
        stylist.describe_all([o], ctx)
    return o

def learn(rows, today=None):
    """Gradual feedback learning. rows: (signature, action, age_days). Returns (recently_rejected, item_affinity).
    Signals fade with a 30-day half-life; one rejection moves an item by only about a third of the scale, so a single
    'not for me' never becomes a permanent dislike. Exact combinations are re-allowed 14 days after a rejection."""
    weight = {"reject": -1.0, "like": 1.0, "wear": 1.5}
    rejected, aff = set(), {}
    for sig, action, age in rows:
        w = weight.get(action)
        if w is None:
            continue
        if action == "reject" and age <= 14:
            rejected.add(sig)
        for part in sig.split("-"):
            if part.isdigit():
                aff[int(part)] = aff.get(int(part), 0.0) + w * 0.5 ** (max(age, 0) / 30)
    return rejected, {k: max(-1.0, min(1.0, v / 3)) for k, v in aff.items()}

def _add_accessories(core, pool, ctx, rng):
    outfit = list(core)
    base = score_outfit(outfit, ctx)["score"]
    for _ in range(2):
        used = {(i["slot"] if i["slot"] == "bag" else i["category"]) for i in outfit if i["slot"] in ("bag", "accessory")}
        best, best_s = None, -1
        for a in pool:
            key = a["slot"] if a["slot"] == "bag" else a["category"]
            if key in used or any(a["id"] == i["id"] for i in outfit):
                continue
            s = score_outfit(outfit + [a], ctx)["score"]
            if s + rng.uniform(0, 2) > best_s:
                best, best_s = a, s + rng.uniform(0, 2)
        if best is None:
            break
        outfit.append(best)
    return outfit

def generate(items, ctx, count=3, seed=None, exclude=frozenset(), rerank=None):
    """Return (outfits, message). Only uses items with status 'available'."""
    rng = random.Random(seed)
    avail = [i for i in items if i["status"] == "available"]
    by = {}
    for i in avail:
        by.setdefault(i["slot"], []).append(i)
    tops, bottoms, dresses, shoes = (by.get(s, []) for s in ("top", "bottom", "dress", "shoes"))
    combos = []
    if shoes and tops and bottoms:
        combos.append((tops, bottoms, shoes))
    if shoes and dresses:
        combos.append((dresses, shoes))
    if not combos:
        need = []
        if not shoes:
            need.append("shoes")
        if not dresses and not (tops and bottoms):
            need.append("a top and a bottom, or a dress")
        return [], "Add " + " and ".join(need) + " to your wardrobe to generate outfits."
    cores = []
    for groups in combos:
        size = 1
        for g in groups:
            size *= len(g)
        if size <= 3000:
            cores += [list(c) for c in itertools.product(*groups)]
        else:
            cores += [[rng.choice(g) for g in groups] for _ in range(3000)]
    scored = sorted(cores, key=lambda c: -(score_outfit(c, ctx)["score"] + rng.uniform(0, 3)))
    pool = by.get("bag", []) + by.get("accessory", [])
    outs = []
    for core in scored[:max(count * 6, 12)]:
        o = build(_add_accessories(core, pool, ctx, rng) if pool else core, ctx)
        o["core_ids"] = {i["id"] for i in core}
        outs.append(o)
    skip = set(exclude) | set(ctx.get("rejected", ()))
    outs = [o for o in outs if o["signature"] not in skip]
    if rerank and outs:                  # optional intelligence service: bounded nudges, reported separately
        for sig, (delta, note) in (rerank(outs) or {}).items():
            for o in outs:
                if o["signature"] == sig:
                    o["score"] = round(max(0, min(100, o["score"] + delta)), 1)
                    o["adjustments"] = {**o.get("adjustments", {}), "intelligence": round(delta, 1)}
                    if note:
                        o["intelligence_note"] = note
    outs.sort(key=lambda o: -(o["score"] + rng.uniform(0, 2)))
    chosen = []
    for relaxed in (False, True):       # prefer outfits that differ in at least two pieces
        for o in outs:
            if len(chosen) >= count:
                break
            if o in chosen:
                continue
            if relaxed or all(len(o["core_ids"] & c["core_ids"]) <= 1 for c in chosen):
                chosen.append(o)
    for o in chosen:
        o.pop("core_ids")
    from . import stylist
    stylist.describe_all(chosen, ctx)
    msg = ""
    if not chosen:
        msg = "You've seen every combination available. Add more items or change the occasion for fresh ideas."
    elif len(chosen) < count:
        msg = f"Only {len(chosen)} distinct outfit(s) are possible with your current wardrobe. Add more items for variety."
    return chosen, msg

def alternatives(items, current_ids, replace_id, ctx, limit=8):
    """Rank available items that could replace `replace_id` while keeping the rest of the outfit."""
    cur = {i["id"]: i for i in items if i["id"] in current_ids}
    old = cur.get(replace_id)
    if old is None:
        raise KeyError(replace_id)
    rest = [i for i in cur.values() if i["id"] != replace_id]
    out = []
    for a in items:
        if a["id"] in cur or a["status"] != "available" or a["slot"] != old["slot"]:
            continue
        if old["slot"] == "accessory" and a["category"] != old["category"]:
            continue
        o = build(rest + [a], ctx)
        out.append({"item": a, "score": o["score"], "item_ids": o["item_ids"]})
    return sorted(out, key=lambda x: -x["score"])[:limit]
