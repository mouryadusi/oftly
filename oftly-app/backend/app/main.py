"""OFTLY API (FastAPI). Local single-user app; also serves the frontend and uploaded media."""
import io
import json
import sqlite3
import tempfile
import zipfile
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import Body, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

import mimetypes
mimetypes.add_type("application/manifest+json", ".webmanifest")
from . import auth, config, db, demo, engine, images, importer, intelligence, security, weather
from .config import ROOT, media_dir
from .models import (SAFE_IMG, CalendarIn, CategoryIn, FeedbackIn, ItemIn, OutfitCtx, OutfitIn, UrlIn, WearIn)

@asynccontextmanager
async def lifespan(_):
    with auth.acct():          # create the accounts database on first start
        pass
    yield

DEBUG = config.flag("DEBUG")
app = FastAPI(title="OFTLY API", version="0.4.0", lifespan=lifespan,
              docs_url="/docs" if DEBUG else None, redoc_url=None, openapi_url="/openapi.json" if DEBUG else None,
              description="OFTLY wardrobe and outfit API. Every route except /api/auth/*, /api/health requires a signed-in session.")
app.include_router(auth.router)
# order matters: the last middleware added is the outermost. LocalGuard (host/origin/headers) -> BodyLimit -> AuthGuard -> app
app.add_middleware(auth.AuthGuard)
app.add_middleware(security.BodyLimit)
app.add_middleware(security.LocalGuard)


@app.exception_handler(Exception)
async def unhandled(request, exc):
    import logging
    logging.getLogger("oftly").exception("Unhandled error on %s %s", request.method, request.url.path)     # details stay in the server log
    from starlette.responses import JSONResponse
    return JSONResponse({"detail": "Something went wrong on our side. Please try again."}, status_code=500)

FIELDS = list(ItemIn.model_fields)
LIST_F = ("secondary_colors", "occasions", "seasons")
ITEM_SELECT = """SELECT i.*, c.label AS category_label, c.slot AS slot,
 (SELECT COUNT(*) FROM calendar cal JOIN outfit_items oi ON oi.outfit_id=cal.outfit_id WHERE oi.item_id=i.id AND cal.worn=1) AS wear_count,
 (SELECT MAX(cal.date) FROM calendar cal JOIN outfit_items oi ON oi.outfit_id=cal.outfit_id WHERE oi.item_id=i.id AND cal.worn=1) AS last_worn
 FROM items i LEFT JOIN categories c ON c.id=i.category"""
PREF_DEFAULTS = {"preferred_styles": [], "favorite_colors": [], "preferred_categories": [], "preferred_occasions": [],
                 "default_occasion": "", "default_season": "", "onboarded": False, "walkthrough_done": False,
                 "preferred_name": "", "gender": "", "city": "", "use_weather": False,
                 "fit": "", "disliked_colors": []}

# ---------- helpers ----------
def row_to_item(r):
    d = dict(r)
    for k in LIST_F:
        d[k] = json.loads(d[k] or "[]")
    d["favorite"], d["is_demo"] = bool(d["favorite"]), bool(d["is_demo"])
    d["image_url"] = f"/media/{d['image']}" if d["image"] else None
    return d

def load_items(c, where="", params=()):
    return [row_to_item(r) for r in c.execute(ITEM_SELECT + where, params)]

def get_item(c, iid):
    rows = load_items(c, " WHERE i.id=?", (iid,))
    if not rows:
        raise HTTPException(404, "Item not found")
    return rows[0]

def check_item(c, m: ItemIn):
    if not c.execute("SELECT 1 FROM categories WHERE id=?", (m.category,)).fetchone():
        raise HTTPException(422, f"Unknown category '{m.category}'")
    if m.image and not (media_dir() / m.image).is_file():
        raise HTTPException(422, "Image not found; upload it first")

def validation_error(e: ValidationError):
    return HTTPException(422, json.loads(e.json()))

def insert_item(c, m: ItemIn, demo_flag=0):
    d = m.model_dump()
    vals = [json.dumps(d[f]) if f in LIST_F else d[f] for f in FIELDS]
    cur = c.execute(f"INSERT INTO items({','.join(FIELDS)},is_demo) VALUES({','.join('?' * (len(FIELDS) + 1))})", vals + [demo_flag])
    return cur.lastrowid

def drop_image_if_unused(c, name):
    if name and not c.execute("SELECT 1 FROM items WHERE image=?", (name,)).fetchone():
        images.remove_image(name)

def cleanup_outfits(c):
    """Remove outfits that no longer have at least two items (e.g. after deleting an item)."""
    c.execute("""DELETE FROM outfits WHERE id NOT IN (SELECT outfit_id FROM outfit_items GROUP BY outfit_id HAVING COUNT(*)>=2)""")

def load_prefs(c):
    out = dict(PREF_DEFAULTS)
    for r in c.execute("SELECT key,value FROM preferences"):
        if r["key"] in out:
            out[r["key"]] = json.loads(r["value"])
    return out

def build_ctx(c, occasion, season=None, destination="", day=0):
    prefs = load_prefs(c)
    if occasion is None:
        occasion = prefs["default_occasion"]
    recent, today = {}, date.today()
    for r in c.execute("SELECT date d, outfit_id o FROM calendar WHERE worn=1 AND date>=?", ((today - timedelta(days=14)).isoformat(),)):
        ids = [x[0] for x in c.execute("SELECT item_id FROM outfit_items WHERE outfit_id=?", (r["o"],))]
        sig = engine.signature(ids)
        recent[sig] = min(recent.get(sig, 99), (today - date.fromisoformat(r["d"])).days)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rows = [(r["signature"], r["action"], (now - datetime.fromisoformat(r["created_at"])).total_seconds() / 86400)
            for r in c.execute("SELECT signature, action, created_at FROM feedback")]
    rejected, affinity = engine.learn(rows)
    place = (destination or "").strip() or prefs["city"]
    wx = weather.lookup(place, day) if prefs["use_weather"] and place else None
    ok = wx if wx and wx.get("available") else None
    return {"occasion": occasion or None, "season": None if ok else (season or None), "prefs": prefs, "today": today,
            "recent_outfits": recent, "rejected": rejected, "affinity": affinity,
            "weather": ok, "climate": ok["band"] if ok else None, "destination": place or None, "weather_raw": wx}

def rerank_hook(ctx):
    """Returns a rerank(outfits) callable for the configured intelligence provider, or None for the built-in engine only."""
    prov = intelligence.get_provider()
    if prov.name == "none":
        return None
    w, prefs = ctx.get("weather") or {}, ctx["prefs"]
    rc = intelligence.base.RankContext(occasion=ctx.get("occasion"), climate_band=ctx.get("climate"), temp_c=w.get("temp_c"),
                                       rain_chance=w.get("rain_chance"), favorite_colors=prefs["favorite_colors"], disliked_colors=prefs["disliked_colors"])
    def run(outs):
        views = [intelligence.base.OutfitView(id=o["signature"], base_score=o["score"], pieces=[
            intelligence.base.PieceView(id=i["id"], slot=i["slot"], category=i["category"], colour=i.get("primary_color") or "",
                                        pattern=i.get("pattern") or "", style=i.get("style") or "", formality=i.get("formality") or 3) for i in o["items"]]) for o in outs]
        return {a.id: (a.delta, a.note) for a in prov.rank_outfits(views, rc)}
    return run

def public(o):
    return {k: v for k, v in o.items() if k != "core_ids"}

def check_ids(c, ids, need_available=True):
    if len(set(ids)) != len(ids):
        raise HTTPException(422, "An outfit cannot contain the same item twice")
    items = load_items(c, f" WHERE i.id IN ({','.join('?' * len(ids))})", ids)
    if len(items) != len(ids):
        raise HTTPException(422, "One or more items do not exist")
    if need_available and any(i["status"] != "available" for i in items):
        raise HTTPException(422, "Unavailable items (laundry/retired) cannot be used")
    return items

def load_outfit(c, oid):
    r = c.execute("SELECT * FROM outfits WHERE id=?", (oid,)).fetchone()
    if not r:
        raise HTTPException(404, "Outfit not found")
    ids = [x[0] for x in c.execute("SELECT item_id FROM outfit_items WHERE outfit_id=?", (oid,))]
    items = engine.sort_items(load_items(c, f" WHERE i.id IN ({','.join('?' * len(ids))})", ids)) if ids else []
    d = dict(r)
    d.update(favorite=bool(d["favorite"]), items=items, item_ids=[i["id"] for i in items],
             signature=engine.signature(ids), all_available=all(i["status"] == "available" for i in items),
             wear_count=c.execute("SELECT COUNT(*) FROM calendar WHERE outfit_id=? AND worn=1", (oid,)).fetchone()[0])
    return d

def save_outfit(c, m: OutfitIn):
    items = check_ids(c, m.item_ids)
    sig = engine.signature(m.item_ids)
    for r in c.execute("SELECT id FROM outfits"):          # same combination already saved -> reuse it
        if engine.signature([x[0] for x in c.execute("SELECT item_id FROM outfit_items WHERE outfit_id=?", (r["id"],))]) == sig:
            return r["id"]
    cur = c.execute("INSERT INTO outfits(name,notes,score,reason) VALUES(?,?,?,?)", (m.name, m.notes, m.score, m.reason))
    c.executemany("INSERT INTO outfit_items VALUES(?,?)", [(cur.lastrowid, i["id"]) for i in items])
    c.execute("INSERT INTO feedback(signature,action) VALUES(?, 'save')", (sig,))
    return cur.lastrowid

def cal_entry(c, r):
    d = dict(r)
    d["worn"] = bool(d["worn"])
    d["outfit"] = load_outfit(c, r["outfit_id"])
    return d

async def read_upload(file: UploadFile):
    data = await file.read(images.MAX_BYTES + 1)
    try:
        return images.save_upload(data)
    except images.UploadError as e:
        raise HTTPException(e.status, str(e))

# ---------- meta ----------
@app.get("/api/health")
def health():
    return {"status": "ok", "app": "OFTLY", "version": app.version}

@app.get("/api/categories")
def categories():
    with db.conn() as c:
        return [dict(r) for r in c.execute("SELECT id,label,slot FROM categories ORDER BY sort,label")]

@app.post("/api/categories", status_code=201)
def add_category(m: CategoryIn):
    with db.conn() as c:
        if c.execute("SELECT 1 FROM categories WHERE id=?", (m.id,)).fetchone():
            raise HTTPException(409, "Category already exists")
        c.execute("INSERT INTO categories VALUES(?,?,?,(SELECT COALESCE(MAX(sort),0)+1 FROM categories))", (m.id, m.label, m.slot))
    return m

@app.get("/api/summary")
def summary():
    with db.conn() as c:
        one = lambda q: c.execute(q).fetchone()[0]
        return {"total": one("SELECT COUNT(*) FROM items"), "available": one("SELECT COUNT(*) FROM items WHERE status='available'"),
                "laundry": one("SELECT COUNT(*) FROM items WHERE status='laundry'"), "favorites": one("SELECT COUNT(*) FROM items WHERE favorite=1"),
                "demo": one("SELECT COUNT(*) FROM items WHERE is_demo=1"), "saved_outfits": one("SELECT COUNT(*) FROM outfits"),
                "by_category": {r["category"]: r["n"] for r in c.execute("SELECT category, COUNT(*) n FROM items GROUP BY category")}}

@app.get("/api/facets")
def facets():
    with db.conn() as c:
        col = lambda f: [r[0] for r in c.execute(f"SELECT DISTINCT {f} FROM items WHERE {f}!='' ORDER BY {f}")]
        return {"colors": col("primary_color"), "brands": col("brand"), "styles": col("style")}

# ---------- items ----------
@app.get("/api/items")
def list_items(q: str = "", category: str = "", color: str = "", brand: str = "", style: str = "", occasion: str = "",
               season: str = "", favorite: Optional[bool] = None, status: str = "", sort: str = "recent",
               unworn_days: int = Query(0, ge=0, le=3650), palette: str = Query("", pattern="^(neutral|colour)?$"),
               min_formality: int = Query(0, ge=0, le=5),
               page: int = Query(1, ge=1), page_size: int = Query(24, ge=1, le=100)):
    w, p = [], []
    if q:
        w.append("(i.name LIKE ? OR i.brand LIKE ? OR i.description LIKE ? OR i.subcategory LIKE ?)")
        p += [f"%{q}%"] * 4
    for col, val in (("i.category", category), ("i.style", style.lower()), ("i.status", status)):
        if val:
            w.append(f"{col}=?")
            p.append(val)
    if color:
        w.append("(i.primary_color=? OR i.secondary_colors LIKE ?)")
        p += [color.lower(), f'%"{color.lower()}"%']
    if brand:
        w.append("i.brand LIKE ?")
        p.append(f"%{brand}%")
    for col, val in (("i.occasions", occasion), ("i.seasons", season)):
        if val:
            w.append(f"{col} LIKE ?")
            p.append(f'%"{val.lower()}"%')
    if favorite is not None:
        w.append("i.favorite=?")
        p.append(int(favorite))
    if unworn_days:        # not worn in the last N days (including never worn)
        w.append("NOT EXISTS (SELECT 1 FROM calendar cal JOIN outfit_items oi ON oi.outfit_id=cal.outfit_id WHERE oi.item_id=i.id AND cal.worn=1 AND cal.date>=?)")
        p.append((date.today() - timedelta(days=unworn_days)).isoformat())
    if palette:
        marks = ",".join("?" * len(engine.NEUTRAL))
        w.append(f"i.primary_color {'IN' if palette == 'neutral' else 'NOT IN'} ({marks}) AND i.primary_color!=''")
        p += sorted(engine.NEUTRAL)
    if min_formality:
        w.append("i.formality>=?")
        p.append(min_formality)
    where = " WHERE " + " AND ".join(w) if w else ""
    order = {"recent": "i.id DESC", "name": "i.name COLLATE NOCASE", "most_worn": "wear_count DESC, i.id DESC",
             "least_worn": "wear_count ASC, i.id DESC"}.get(sort, "i.id DESC")
    with db.conn() as c:
        total = c.execute(f"SELECT COUNT(*) FROM items i{where}", p).fetchone()[0]
        items = load_items(c, f"{where} ORDER BY {order} LIMIT ? OFFSET ?", p + [page_size, (page - 1) * page_size])
    return {"items": items, "total": total, "page": page, "pages": max(1, -(-total // page_size))}

@app.post("/api/items", status_code=201)
def create_item(m: ItemIn):
    with db.conn() as c:
        check_item(c, m)
        return get_item(c, insert_item(c, m))

@app.get("/api/items/{iid}")
def read_item(iid: int):
    with db.conn() as c:
        return get_item(c, iid)

@app.patch("/api/items/{iid}")
def update_item(iid: int, patch: dict = Body(...)):
    with db.conn() as c:
        cur = get_item(c, iid)
        unknown = set(patch) - set(FIELDS)
        if unknown:
            raise HTTPException(422, f"Unknown fields: {sorted(unknown)}")
        try:
            m = ItemIn(**{**{f: cur[f] for f in FIELDS}, **patch})
        except ValidationError as e:
            raise validation_error(e)
        check_item(c, m)
        d = m.model_dump()
        c.execute(f"UPDATE items SET {','.join(f + '=?' for f in FIELDS)} WHERE id=?",
                  [json.dumps(d[f]) if f in LIST_F else d[f] for f in FIELDS] + [iid])
        if cur["image"] != m.image:
            drop_image_if_unused(c, cur["image"])
        return get_item(c, iid)

@app.delete("/api/items/{iid}", status_code=204)
def delete_item(iid: int):
    with db.conn() as c:
        cur = get_item(c, iid)
        c.execute("DELETE FROM items WHERE id=?", (iid,))
        cleanup_outfits(c)
        drop_image_if_unused(c, cur["image"])

@app.post("/api/uploads", status_code=201)
async def upload(file: UploadFile = File(...)):
    auth.throttle(f"upload:{config.current_uid()}", 60, 60)                                   # 60 uploads/minute/user
    if sum(1 for _ in media_dir().glob("*.jpg")) >= int(config.env("MAX_PHOTOS", 1000)):
        raise HTTPException(413, "Photo limit reached. Delete some photos first.")
    name, color = await read_upload(file)
    return {"image": name, "image_url": f"/media/{name}", "suggested_color": color}

@app.post("/api/import-url")
def import_url(body: UrlIn):
    return importer.import_product(body.url.strip())

# ---------- outfits ----------
@app.get("/api/outfits/generate")
def generate(occasion: Optional[str] = None, season: Optional[str] = None, destination: str = Query("", max_length=80),
             day: int = Query(0, ge=0, le=weather.MAX_DAY), count: int = Query(3, ge=1, le=8),
             seed: Optional[int] = None, exclude: str = ""):
    with db.conn() as c:
        ctx = build_ctx(c, occasion, season, destination, day)
        outs, msg = engine.generate(load_items(c), ctx, count, seed, set(filter(None, exclude.split(";"))), rerank=rerank_hook(ctx))
    return {"outfits": [public(o) for o in outs], "message": msg, "destination": ctx["destination"], "weather": ctx["weather_raw"]}

@app.post("/api/outfits/alternatives")
def outfit_alternatives(m: OutfitCtx):
    if m.replace_id is None:
        raise HTTPException(422, "replace_id is required")
    with db.conn() as c:
        check_ids(c, m.item_ids, need_available=False)
        try:
            alts = engine.alternatives(load_items(c), set(m.item_ids), m.replace_id, build_ctx(c, m.occasion, m.season, m.destination, m.day), m.limit)
        except KeyError:
            raise HTTPException(422, "replace_id is not part of this outfit")
    return {"alternatives": alts}

@app.post("/api/outfits/evaluate")
def evaluate(m: OutfitCtx):
    with db.conn() as c:
        items = check_ids(c, m.item_ids, need_available=False)
        return public(engine.build(items, build_ctx(c, m.occasion, m.season, m.destination, m.day), describe=True))

@app.post("/api/outfits", status_code=201)
def create_outfit(m: OutfitIn):
    with db.conn() as c:
        return load_outfit(c, save_outfit(c, m))

@app.get("/api/outfits")
def list_outfits():
    with db.conn() as c:
        return [load_outfit(c, r[0]) for r in c.execute("SELECT id FROM outfits ORDER BY id DESC")]

@app.get("/api/outfits/{oid}")
def read_outfit(oid: int):
    with db.conn() as c:
        return load_outfit(c, oid)

@app.patch("/api/outfits/{oid}")
def update_outfit(oid: int, patch: dict = Body(...)):
    with db.conn() as c:
        load_outfit(c, oid)
        if "name" in patch:
            c.execute("UPDATE outfits SET name=? WHERE id=?", (str(patch["name"])[:120], oid))
        if "notes" in patch:
            c.execute("UPDATE outfits SET notes=? WHERE id=?", (str(patch["notes"])[:2000], oid))
        if "favorite" in patch:
            c.execute("UPDATE outfits SET favorite=? WHERE id=?", (int(bool(patch["favorite"])), oid))
        if "item_ids" in patch:
            ids = patch["item_ids"]
            if not isinstance(ids, list) or len(ids) < 2 or not all(isinstance(i, int) for i in ids):
                raise HTTPException(422, "item_ids must be a list of at least two item ids")
            check_ids(c, ids)
            c.execute("DELETE FROM outfit_items WHERE outfit_id=?", (oid,))
            c.executemany("INSERT INTO outfit_items VALUES(?,?)", [(oid, i) for i in ids])
        return load_outfit(c, oid)

@app.delete("/api/outfits/{oid}", status_code=204)
def delete_outfit(oid: int):
    with db.conn() as c:
        load_outfit(c, oid)
        c.execute("DELETE FROM outfits WHERE id=?", (oid,))

@app.post("/api/outfits/{oid}/wear", status_code=201)
def wear(oid: int, body: WearIn = WearIn()):
    with db.conn() as c:
        load_outfit(c, oid)
        cur = c.execute("INSERT INTO calendar(date,outfit_id,worn) VALUES(?,?,1)", ((body.date or date.today()).isoformat(), oid))
        ids = [x[0] for x in c.execute("SELECT item_id FROM outfit_items WHERE outfit_id=?", (oid,))]
        c.execute("INSERT INTO feedback(signature,action) VALUES(?,?)", (engine.signature(ids), "wear"))
        return cal_entry(c, c.execute("SELECT * FROM calendar WHERE id=?", (cur.lastrowid,)).fetchone())

@app.post("/api/feedback", status_code=201)
def feedback(m: FeedbackIn):
    with db.conn() as c:
        c.execute("INSERT INTO feedback(signature,action) VALUES(?,?)", (engine.signature(m.item_ids), m.action))
    return {"ok": True}

# ---------- calendar & history ----------
@app.get("/api/calendar")
def calendar(start: date, end: date):
    with db.conn() as c:
        return [cal_entry(c, r) for r in c.execute("SELECT * FROM calendar WHERE date BETWEEN ? AND ? ORDER BY date,id", (start.isoformat(), end.isoformat()))]

@app.post("/api/calendar", status_code=201)
def plan(m: CalendarIn):
    with db.conn() as c:
        load_outfit(c, m.outfit_id)
        cur = c.execute("INSERT INTO calendar(date,outfit_id,worn,notes) VALUES(?,?,?,?)", (m.date.isoformat(), m.outfit_id, int(m.worn), m.notes))
        return cal_entry(c, c.execute("SELECT * FROM calendar WHERE id=?", (cur.lastrowid,)).fetchone())

@app.patch("/api/calendar/{cid}")
def update_calendar(cid: int, patch: dict = Body(...)):
    with db.conn() as c:
        if not c.execute("SELECT 1 FROM calendar WHERE id=?", (cid,)).fetchone():
            raise HTTPException(404, "Calendar entry not found")
        if "worn" in patch:
            c.execute("UPDATE calendar SET worn=? WHERE id=?", (int(bool(patch["worn"])), cid))
        if "notes" in patch:
            c.execute("UPDATE calendar SET notes=? WHERE id=?", (str(patch["notes"])[:1000], cid))
        if "date" in patch:
            try:
                c.execute("UPDATE calendar SET date=? WHERE id=?", (date.fromisoformat(str(patch["date"])).isoformat(), cid))
            except ValueError:
                raise HTTPException(422, "date must be YYYY-MM-DD")
        return cal_entry(c, c.execute("SELECT * FROM calendar WHERE id=?", (cid,)).fetchone())

@app.delete("/api/calendar/{cid}", status_code=204)
def delete_calendar(cid: int):
    with db.conn() as c:
        c.execute("DELETE FROM calendar WHERE id=?", (cid,))

@app.get("/api/history")
def history(days: int = Query(60, ge=1, le=730)):
    """Worn outfits (newest first) with repeat warnings, plus basic rotation suggestions."""
    today = date.today()
    with db.conn() as c:
        rows = c.execute("SELECT * FROM calendar WHERE worn=1 AND date>=? AND date<=? ORDER BY date,id", ((today - timedelta(days=days)).isoformat(), today.isoformat())).fetchall()
        entries, seen = [], []
        for r in rows:
            e = cal_entry(c, r)
            d = date.fromisoformat(e["date"])
            ids = set(e["outfit"]["item_ids"])
            e["repeat_of"] = next((p["date"] for p in reversed(seen) if p["sig"] == e["outfit"]["signature"] and (d - p["d"]).days <= 14), None)
            shared = ids & {i for p in seen if 0 <= (d - p["d"]).days <= 7 for i in p["ids"]}
            e["recent_items"] = [i["name"] for i in e["outfit"]["items"] if i["id"] in shared]
            seen.append({"d": d, "sig": e["outfit"]["signature"], "ids": ids, "date": e["date"]})
            entries.append(e)
        cutoff = (today - timedelta(days=30)).isoformat()
        avail = [i for i in load_items(c, " WHERE i.status='available'") if i["slot"] in engine.CORE or i["slot"] == "shoes"]
        stale = sorted((i for i in avail if not i["last_worn"] or i["last_worn"] < cutoff), key=lambda i: i["last_worn"] or "")[:12]
    return {"entries": entries[::-1], "rotation": {"not_worn_recently": stale}}

# ---------- preferences, data, demo ----------
@app.get("/api/preferences")
def get_prefs():
    with db.conn() as c:
        return load_prefs(c)

@app.get("/api/weather")
def get_weather(destination: str = Query("", max_length=80), day: int = Query(0, ge=0, le=weather.MAX_DAY)):
    """Forecast for a destination (default: home city), only if the user opted in. Never fabricated."""
    with db.conn() as c:
        p = load_prefs(c)
    place = destination.strip() or p["city"]
    if not p["use_weather"]:
        return {"available": False, "off": True, "reason": "Weather is off. Turn it on in Settings to use destination forecasts."}
    if not place:
        return {"available": False, "reason": "Add a destination or a home city to see a forecast."}
    return weather.lookup(place, day)

@app.get("/api/intelligence/status")
def intelligence_status():
    return intelligence.get_provider().status()

@app.get("/api/items/{iid}/suggestions")
def item_suggestions(iid: int):
    """Model *suggestions* for an item's photo. Empty unless an intelligence provider is configured. Never auto-applied."""
    with db.conn() as c:
        it = get_item(c, iid)
    if not it.get("image"):
        return {"suggestions": [], "note": "This item has no photo."}
    path = media_dir() / it["image"]
    if not path.is_file():
        return {"suggestions": [], "note": "Photo file is missing."}
    sug = intelligence.get_provider().suggest_attributes(path.read_bytes(), "image/jpeg")
    return {"suggestions": [s.model_dump() for s in sug], "confirmed": False}

@app.get("/api/insights")
def insights():
    """Wardrobe insights computed only from real records (no estimates)."""
    today = date.today()
    with db.conn() as c:
        items = load_items(c)
        weeks = [0] * 8
        for r in c.execute("SELECT date d, COUNT(*) n FROM calendar WHERE worn=1 GROUP BY date"):
            ago = (today - date.fromisoformat(r["d"])).days
            if 0 <= ago < 56:
                weeks[7 - ago // 7] += r["n"]
    live = [i for i in items if i["status"] != "retired"]
    cutoff = (today - timedelta(days=30)).isoformat()
    coloured = [i for i in live if i.get("primary_color")]
    colours = {}
    for i in coloured:
        colours[i["primary_color"]] = colours.get(i["primary_color"], 0) + 1
    cpw = sorted(({"id": i["id"], "name": i["name"], "per_wear": round(i["price"] / i["wear_count"], 2), "wears": i["wear_count"], "price": i["price"]}
                  for i in live if i.get("price") and i["wear_count"]), key=lambda x: x["per_wear"])
    return {"total": len(live), "worn_30d": sum(1 for i in live if i["last_worn"] and i["last_worn"] >= cutoff),
            "never_worn": sum(1 for i in live if not i["wear_count"]),
            "dormant_60d": sum(1 for i in live if not i["last_worn"] or i["last_worn"] < (today - timedelta(days=60)).isoformat()),
            "colours": sorted(colours.items(), key=lambda kv: -kv[1])[:10],
            "neutral_share": round(sum(1 for i in coloured if i["primary_color"] in engine.NEUTRAL) / len(coloured), 2) if coloured else None,
            "most_worn": [{"id": i["id"], "name": i["name"], "wears": i["wear_count"], "image_url": i.get("image_url")}
                          for i in sorted(live, key=lambda i: -i["wear_count"])[:5] if i["wear_count"]],
            "cost_per_wear": cpw[:3], "wears_by_week": weeks,
            "sites": [{"id": i["id"], "name": i["name"], "colour": i.get("primary_color") or "", "formality": i.get("formality") or 3,
                       "category": i["category"], "slot": i["slot"], "wears": i["wear_count"]} for i in live][:200]}

@app.get("/api/engine")
def engine_info():
    return {"weights": engine.WEIGHTS}

@app.put("/api/preferences")
def put_prefs(body: dict = Body(...)):
    unknown = set(body) - set(PREF_DEFAULTS)
    if unknown:
        raise HTTPException(422, f"Unknown preferences: {sorted(unknown)}")
    with db.conn() as c:
        for k, v in body.items():
            if not isinstance(v, type(PREF_DEFAULTS[k])):
                raise HTTPException(422, f"'{k}' has the wrong type")
            if isinstance(v, str) and len(v) > 80 or isinstance(v, list) and (len(v) > 30 or any(not isinstance(x, str) or len(x) > 40 for x in v)):
                raise HTTPException(422, f"'{k}' is too long")
            if k == "gender" and v not in ("", "woman", "man", "non-binary", "self-describe", "prefer-not-to-say"):
                raise HTTPException(422, "Unknown gender option")
            c.execute("INSERT INTO preferences VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, json.dumps(v)))
        return load_prefs(c)

@app.post("/api/demo", status_code=201)
def load_demo():
    if not config.demo_enabled():
        raise HTTPException(404, "Not found")
    with db.conn() as c:
        if c.execute("SELECT 1 FROM items WHERE is_demo=1").fetchone():
            raise HTTPException(409, "Demo items are already loaded")
        for d in demo.build_items():
            insert_item(c, ItemIn(**d), 1)
    return {"added": len(demo.DEMO)}

@app.delete("/api/demo")
def remove_demo():
    if not config.demo_enabled():
        raise HTTPException(404, "Not found")
    with db.conn() as c:
        names = [r[0] for r in c.execute("SELECT image FROM items WHERE is_demo=1")]
        n = c.execute("DELETE FROM items WHERE is_demo=1").rowcount
        cleanup_outfits(c)
        for name in names:
            drop_image_if_unused(c, name)
    return {"removed": n}

@app.get("/api/export")
def export_json():
    with db.conn() as c:
        data = {t: [dict(r) for r in c.execute(f"SELECT * FROM {t}")] for t in
                ("categories", "items", "outfits", "outfit_items", "calendar", "feedback", "preferences")}
    return Response(json.dumps(data, indent=1), media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="oftly-export.json"'})

@app.get("/api/export/backup")
def backup_zip():
    """ZIP with a consistent copy of the database and all photos."""
    buf = io.BytesIO()
    with tempfile.TemporaryDirectory() as td, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        src, dst = db.connect(), sqlite3.connect(Path(td) / "oftly.db")
        src.backup(dst)
        src.close(); dst.close()
        z.write(Path(td) / "oftly.db", "oftly.db")
        for f in media_dir().glob("*.jpg"):
            z.write(f, f"media/{f.name}")
    return Response(buf.getvalue(), media_type="application/zip", headers={"Content-Disposition": 'attachment; filename="oftly-backup.zip"'})

@app.delete("/api/data")
def delete_all(confirm: bool = False):
    if not confirm:
        raise HTTPException(400, "Pass confirm=true to delete all wardrobe data")
    with db.conn() as c:
        for t in ("calendar", "outfit_items", "outfits", "feedback", "items", "preferences"):
            c.execute(f"DELETE FROM {t}")
    for f in media_dir().glob("*.jpg"):
        f.unlink()
    return {"deleted": True}

# ---------- static ----------

@app.get("/media/{name}")
def media(name: str):
    """Serve a photo by validated name only (blocks path traversal)."""
    f = media_dir() / name
    if not SAFE_IMG.match(name) or not f.is_file():
        raise HTTPException(404, "Image not found")
    return FileResponse(f, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})

app.mount("/", StaticFiles(directory=str(ROOT / "frontend"), html=True), name="frontend")
