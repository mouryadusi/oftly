"""Grounded outfit narration.

Every sentence is derived from fields that exist on the item dicts (name, colour, pattern, formality, tags,
favourite, last_worn) or from the context the user supplied (occasion, season, preferences, weather, feedback).
OFTLY has no fit, fabric, warmth or silhouette data, so it never describes them; `not_assessed` says so explicitly.
Wording varies deterministically (crc32 of the outfit), so an outfit always reads the same but different outfits differ.
"""
import zlib
from datetime import date

from . import engine
from .engine import HUE, NEUTRAL, OCC_FORMALITY, PLAIN, norm

FORMAL = {1: "very casual", 2: "casual", 3: "smart casual", 4: "dressy", 5: "formal"}
FACTOR_LABEL = {"color": "Colour harmony", "formality": "Formality match", "occasion": "Occasion fit",
                "season": "Weather fit", "preference": "Your taste", "freshness": "Variety"}
NOT_ASSESSED = ["fit and silhouette", "fabric, warmth and breathability"]
TITLES = {
    "neutral": ["Quiet Neutrals", "The Understated Edit", "Tonal Ease", "Soft Foundations"],
    "tonal": ["{C} Study", "All {C}", "Head-to-Toe {C}"],
    "accent": ["{C} Note", "A Touch of {C}", "{C} Accent"],
    "pair": ["{C1} & {C2}", "{C1} Meets {C2}"],
    "busy": ["The Colour Edit", "Colour Play"],
    "unknown": ["Everyday Edit"],
}


def _pick(options, key, salt=""):
    return options[zlib.crc32(f"{key}|{salt}".encode()) % len(options)]

def _join(xs):
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1] if xs else ""

def _col(i): return norm(i.get("primary_color"))
def _metal(i): return i.get("slot") == "accessory" and _col(i) in ("gold", "silver")
def _accent(i): return bool(_col(i)) and _col(i) not in NEUTRAL and not _metal(i)
def _patterned(i): return norm(i.get("pattern")) not in PLAIN
def _label(i): return (i.get("category_label") or i.get("category") or "piece").lower()
def _fl(f): return FORMAL.get(round(f), "smart casual")


def palette(items):
    cols = list(dict.fromkeys(_col(i) for i in items if _col(i) and not _metal(i)))
    acc = [c for c in cols if c not in NEUTRAL]
    if not cols: return "unknown", cols, acc
    if len(cols) == 1: return "tonal", cols, acc
    if not acc: return "neutral", cols, acc
    return {1: "accent", 2: "pair"}.get(len(acc), "busy"), cols, acc


def colour_story(kind, cols, acc):
    neutrals = [c for c in cols if c in NEUTRAL]
    if kind == "unknown":
        return "Colours aren't recorded for these pieces, so OFTLY can't comment on the palette."
    if kind == "tonal":
        return f"A head-to-toe {cols[0]} look, so cohesion is built in."
    if kind == "neutral":
        return f"An all-neutral palette ({_join(cols)}): every pairing works and nothing competes."
    if kind == "accent":
        return f"{acc[0].capitalize()} is the only colour here; {_join(neutrals)} {'keeps' if len(neutrals) == 1 else 'keep'} everything else quiet."
    if kind == "pair":
        a, b = HUE.get(acc[0]), HUE.get(acc[1])
        rel = "two accent colours"
        if a is not None and b is not None:
            d = min(abs(a - b), 360 - abs(a - b))
            rel = ("two accents close on the colour wheel" if d <= 40 else
                   "two accents opposite each other on the colour wheel" if d >= 150 else "two accents in a looser pairing")
        return f"{acc[0].capitalize()} and {acc[1]} are {rel}" + (f", grounded by {_join(neutrals)}." if neutrals else ".")
    return f"{len(acc)} accent colours at once ({_join(acc)}), the boldest mix on offer, so keep everything else simple."


def focal(items):
    best, best_s = None, 0.0
    for i in items:
        s = (3 if _accent(i) else 0) + (2 if _patterned(i) else 0) + (1.5 if i["slot"] == "dress" else 0)
        if s > best_s:
            best, best_s = i, s
    return best


def focal_text(f, items):
    if f is None:
        return "No single standout piece: the look is neutral and plain throughout, so it reads understated rather than attention-led."
    why = (f"{f['name']} carries the only colour ({_col(f)})" if _accent(f) and sum(_accent(i) for i in items) == 1 else
           f"{f['name']} is the boldest colour here ({_col(f)})" if _accent(f) else
           f"the {norm(f.get('pattern'))} pattern on {f['name']} is the busiest detail" if _patterned(f) else
           f"{f['name']} carries the look on its own")
    rest = [i for i in items if i["id"] != f["id"]]
    quiet = all(not _accent(i) and not _patterned(i) for i in rest)
    tail = ("everything else is neutral and plain, so it can lead." if quiet else
            "other pieces also carry colour or pattern, so there is more than one point of interest.")
    return f"Focal point: {why[0].upper()}{why[1:]}; {tail}"


NEUTRAL_NOTE = {
    "top": ["{C} carries the upper half quietly.", "{C} keeps the top of the look calm."],
    "bottom": ["{C} anchors the lower half.", "{C} gives the look a steady base."],
    "dress": ["{C} lets the dress stay simple.", "A quiet {c} dress that needs little else."],
    "shoes": ["{C} grounds the look from the floor up.", "{C} finishes the look at ground level."],
    "bag": ["{C} keeps the bag understated.", "A low-key {c} bag."],
    "accessory": ["{C} stays in the background.", "A quiet {c} detail."],
}


def piece_note(i, items, f, key):
    c, others = _col(i), [o for o in items if o["id"] != i["id"]]
    desc = " ".join(x for x in [norm(i.get("pattern")) if _patterned(i) else "", c] if x)
    echo = next((o for o in others if c and _col(o) == c), None)
    if f is not None and i["id"] == f["id"]:
        s = _pick([f"{desc.capitalize() or 'This piece'} is the focal point; the rest is built around it.",
                   f"The statement piece: {desc or 'it sets the tone'}."], key, i["id"])
    elif echo:
        s = f"Its {c} repeats in the {echo['name']}, which ties the look together."
    elif f is not None and _accent(f) and c in NEUTRAL:
        s = f"A neutral {c} that lets {f['name']} lead."
    elif _metal(i):
        s = f"A restrained {c} finish."
    elif c in NEUTRAL:
        s = _pick(NEUTRAL_NOTE.get(i["slot"], NEUTRAL_NOTE["accessory"]), key, i["id"]).format(C=c.capitalize(), c=c)
    elif c:
        s = f"Adds {desc} as a secondary note."
    else:
        s = "Colour isn't recorded, so OFTLY can't comment on how it pairs."
    fm = [o.get("formality") or 3 for o in items]
    v, avg = i.get("formality") or 3, sum(fm) / len(fm)
    if v - avg >= 1:
        s += f" Reads {FORMAL.get(v)}, the dressier end of this outfit."
    elif avg - v >= 1:
        s += f" Reads {FORMAL.get(v)}, the more relaxed end of this outfit."
    if i.get("favorite"):
        s += " One of your favourites."
    return s


def intention(items, ctx):
    n, occ = len(items), norm(ctx.get("occasion"))
    avg = sum(i.get("formality") or 3 for i in items) / n
    if occ:
        tagged = [i for i in items if occ in (i.get("occasions") or [])]
        s = (f"Styled for {occ}: {len(tagged)} of {n} pieces are tagged for it, and the formality sits at {_fl(avg)}." if tagged else
             f"You asked for {occ}, but none of these pieces are tagged for it, so this leans on formality alone ({_fl(avg)}).")
        t = OCC_FORMALITY.get(occ)
        if t and avg - t >= 1.5: s += f" That is dressier than {occ} usually calls for."
        elif t and t - avg >= 1.5: s += f" That is more relaxed than {occ} usually calls for."
    else:
        s = f"No occasion chosen, so this is styled as an easy everyday look at {_fl(avg)} level."
    imp = norm(ctx.get("impression"))
    kind, _, _ = palette(items)
    checks = {"understated": kind in ("neutral", "tonal") and not any(_patterned(i) for i in items),
              "confident": any(_accent(i) for i in items) or avg >= 4,
              "casual": avg <= 2.5, "polished": avg >= 4 and max(i.get("formality") or 3 for i in items) - min(i.get("formality") or 3 for i in items) <= 1}
    if imp in checks:
        s += f" For a {imp} impression, it {'fits' if checks[imp] else 'only partly fits'} based on colour and formality."
    return s


def practical(items, ctx):
    n, out, w = len(items), [], ctx.get("weather")
    fits = lambda band: sum(1 for i in items if band in (i.get("seasons") or []) or "all" in (i.get("seasons") or []))
    if w:
        t, where = w.get("temp_c"), w.get("city") or "your destination"
        when = {0: "today", 1: "tomorrow"}.get(w.get("day", 0), f"in {w.get('day')} days")
        if t is not None:
            band = w.get("band") or ("winter" if t <= 10 else "autumn" if t <= 17 else "spring" if t <= 25 else "summer")
            label = {"winter": "cold", "autumn": "cool", "spring": "mild", "summer": "hot"}[band]
            line = f"{where}, {when}: {t:.0f}°C ({label}). {fits(band)} of {n} pieces are tagged for this climate."
            if band == "winter":
                line += " OFTLY can't tell how warm a piece is, so add a layer if you'll be out for long."
            elif band == "summer":
                line += " OFTLY can't judge breathability from photos."
            out.append(line)
        if (w.get("rain_chance") or 0) >= 50:
            shoes = next((i["name"] for i in items if i["slot"] == "shoes"), None)
            out.append(f"Rain is likely ({w['rain_chance']}%). OFTLY doesn't record whether shoes are waterproof" + (f", so check {shoes}." if shoes else "."))
        if (w.get("humidity") or 0) >= 75:
            out.append(f"Humid ({w['humidity']}%). OFTLY has no fabric data, so choose by how you know each piece feels in humidity.")
        if (w.get("wind_kph") or 0) >= 30:
            out.append(f"Windy ({w['wind_kph']:.0f} km/h). OFTLY has no fit data, so judge layers and hems yourself.")
    season = norm(ctx.get("season"))
    if season and not w:
        out.append(f"{sum(1 for i in items if season in (i.get('seasons') or []))} of {n} pieces are tagged {season}.")
    return out or ["No weather was used for this suggestion. Add a destination to plan around its forecast."]


def why_for_you(items, ctx, result=None):
    prefs, aff, today = ctx.get("prefs") or {}, ctx.get("affinity") or {}, ctx.get("today") or date.today()
    fav_c = {norm(x) for x in prefs.get("favorite_colors", [])}
    fav_s = {norm(x) for x in prefs.get("preferred_styles", [])}
    dis = {norm(x) for x in prefs.get("disliked_colors", [])}
    out = []
    hit = [i for i in items if _col(i) in fav_c]
    if hit:
        many = len({_col(i) for i in hit}) > 1
        out.append(f"Favourite colour{'s' if many else ''} {_join(dict.fromkeys(_col(i) for i in hit))} {'show' if many else 'shows'} up in {_join([i['name'] for i in hit])}.")
    hit = [i for i in items if norm(i.get("style")) in fav_s]
    if hit: out.append(f"Style preference matched by {_join([i['name'] for i in hit])}.")
    hit = [i for i in items if i.get("favorite")]
    if hit: out.append(f"Includes your favourite{'s' if len(hit) > 1 else ''}: {_join([i['name'] for i in hit])}.")
    hit = [i for i in items if aff.get(i["id"], 0) > 0.3]
    if hit: out.append(f"You've responded well to outfits with {_join([i['name'] for i in hit])}.")
    hit = [i for i in items if _col(i) in dis]
    if hit: out.append(f"Includes {_join(dict.fromkeys(_col(i) for i in hit))}, a colour you said you avoid, so it scored lower.")
    aged = [(i, (today - date.fromisoformat(i["last_worn"])).days) for i in items if i.get("last_worn")]
    never = [i for i in items if not i.get("last_worn")]
    if aged and max(d for _, d in aged) >= 21:
        i, d = max(aged, key=lambda x: x[1])
        out.append(f"{i['name']} was last worn {d} days ago.")
    elif never and aged:
        out.append(f"No wear is recorded yet for {never[0]['name']}.")
    if result and result.get("intelligence_note"):
        out.append(f"OFTLY Intelligence: {result['intelligence_note']}")
    return out or ["OFTLY doesn't know enough about your taste yet. Use Save or Not for me and it will start to learn."]


def describe(items, result, ctx):
    items = [{**i, "name": i.get("name") or _label(i).capitalize()} for i in engine.sort_items(items)]
    key = engine.signature([i["id"] for i in items])
    kind, cols, acc = palette(items)
    cs, f = colour_story(kind, cols, acc), focal(items)
    metals = [i for i in items if _metal(i)]
    if metals and kind != "unknown":
        cs += f" {_join([i['name'] for i in metals])} adds a restrained {_join(dict.fromkeys(_col(i) for i in metals))} finish."
    ft = focal_text(f, items)
    cap = lambda c: c.title()
    tpl = _pick(TITLES[kind], key)
    main_c = acc[0] if kind == "accent" else cols[0] if cols else ""
    title = tpl.format(C=cap(main_c), C1=cap(acc[0]) if acc else "", C2=cap(acc[1]) if len(acc) > 1 else "")
    occ = norm(ctx.get("occasion"))
    if occ: title += f" · {occ.capitalize()}"
    bd = result["breakdown"]
    ranked = sorted(bd.items(), key=lambda kv: -kv[1])
    return {
        "title": title, "intention": intention(items, ctx),
        "pieces": [{"id": i["id"], "name": i["name"], "role": _label(i), "note": piece_note(i, items, f, key)} for i in items],
        "focal_point": {"item_id": f["id"] if f else None, "text": ft},
        "colour_story": cs, "practical": practical(items, ctx), "why_for_you": why_for_you(items, ctx, result),
        "factors": [{"key": k, "label": FACTOR_LABEL.get(k, k), "value": v} for k, v in ranked[:3]],
        "weakest": ({"label": FACTOR_LABEL.get(ranked[-1][0]), "value": ranked[-1][1]} if ranked[-1][1] < 60 else None),
        "adjustments": result.get("adjustments", {}), "not_assessed": NOT_ASSESSED,
        "summary": f"{cs} {ft}"[:900],
    }


def describe_all(outfits, ctx):
    """Attach `style` to each outfit, make titles unique within the batch, and set `reason` to the grounded summary."""
    seen = set()
    for o in outfits:
        s = describe(o["items"], o, ctx)
        if s["title"] in seen:
            fi = next((p["name"] for p in s["pieces"] if p["id"] == s["focal_point"]["item_id"]), s["pieces"][0]["name"])
            s["title"] += f": {fi}"
        seen.add(s["title"])
        o["style"], o["reason"] = s, s["summary"]
    return outfits
