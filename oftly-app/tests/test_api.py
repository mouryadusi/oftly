import io
import zipfile
from conftest import add, basic_wardrobe, png

def test_item_crud(client):
    it = add(client, "Blue shirt", "shirts", primary_color="Blue", occasions=["Work"])
    assert it["primary_color"] == "blue" and it["occasions"] == ["work"] and it["category_label"] == "Shirts"
    assert client.get("/api/items").json()["total"] == 1
    r = client.patch(f"/api/items/{it['id']}", json={"name": "Navy shirt", "favorite": True, "status": "laundry"})
    assert r.json()["name"] == "Navy shirt" and r.json()["favorite"] and r.json()["status"] == "laundry"
    assert client.get(f"/api/items/{it['id']}").json()["name"] == "Navy shirt"   # persisted
    assert client.delete(f"/api/items/{it['id']}").status_code == 204
    assert client.get(f"/api/items/{it['id']}").status_code == 404

def test_invalid_inputs(client):
    bad = [{"name": "", "category": "shirts"}, {"name": "x", "category": "nope"},
           {"name": "x", "category": "shirts", "formality": 9}, {"name": "x", "category": "shirts", "price": -1},
           {"name": "x", "category": "shirts", "product_url": "javascript:alert(1)"},
           {"name": "x", "category": "shirts", "image": "../../etc/passwd"},
           {"name": "x", "category": "shirts", "image": "missing.jpg"}]
    for b in bad:
        assert client.post("/api/items", json=b).status_code == 422, b
    it = add(client)
    assert client.patch(f"/api/items/{it['id']}", json={"formality": 0}).status_code == 422
    assert client.patch(f"/api/items/{it['id']}", json={"bogus": 1}).status_code == 422

def test_upload_and_serve(client):
    r = client.post("/api/uploads", files={"file": ("a.png", png((200, 30, 30)), "image/png")})
    assert r.status_code == 201 and r.json()["suggested_color"] in ("red", "burgundy")
    it = add(client, "Red tee", "tshirts", image=r.json()["image"])
    img = client.get(it["image_url"])
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg"
    client.delete(f"/api/items/{it['id']}")
    assert client.get(it["image_url"]).status_code == 404       # file removed with the item

def test_invalid_uploads(client):
    assert client.post("/api/uploads", files={"file": ("a.txt", b"hello", "text/plain")}).status_code == 400
    assert client.post("/api/uploads", files={"file": ("a.png", b"", "image/png")}).status_code == 400
    assert client.post("/api/uploads", files={"file": ("a.png", b"\x89PNG" + b"0" * 9_000_000, "image/png")}).status_code == 413
    assert client.get("/media/..%2Foftly.db").status_code == 404
    assert client.get("/media/notes.txt").status_code == 404

def test_filter_search_sort_pagination(client):
    add(client, "Red shirt", "shirts", primary_color="red", brand="Acme", favorite=True, seasons=["summer"], occasions=["party"])
    add(client, "Blue jeans", "jeans_shorts", primary_color="blue", brand="Denimco", style="casual")
    add(client, "Green tee", "tshirts", primary_color="green")
    g = lambda q: client.get("/api/items?" + q).json()
    assert g("category=shirts")["total"] == 1 and g("q=jeans")["total"] == 1 and g("color=blue")["total"] == 1
    assert g("favorite=true")["total"] == 1 and g("brand=acme")["total"] == 1 and g("season=summer")["total"] == 1
    assert g("occasion=party")["total"] == 1 and g("style=casual")["total"] == 1
    assert [i["name"] for i in g("sort=name")["items"]][0] == "Blue jeans"
    assert g("page_size=2")["pages"] == 2 and len(g("page=2&page_size=2")["items"]) == 1
    assert g("sort=recent")["items"][0]["name"] == "Green tee"

def test_generate_outfits(client):
    basic_wardrobe(client)
    r = client.get("/api/outfits/generate?count=3&seed=1").json()
    assert len(r["outfits"]) >= 2
    sigs = [o["signature"] for o in r["outfits"]]
    assert len(set(sigs)) == len(sigs)
    for o in r["outfits"]:
        assert len(set(o["item_ids"])) == len(o["item_ids"]) and 0 <= o["score"] <= 100 and o["reason"]
        cats = {i["category"] for i in o["items"]}
        assert "shoes" in cats and (("shirts" in cats or "tshirts" in cats) and ("pants" in cats or "jeans_shorts" in cats))
    more = client.get(f"/api/outfits/generate?count=3&seed=2&exclude={';'.join(sigs)}").json()
    assert not set(sigs) & {o["signature"] for o in more["outfits"]}

def test_unavailable_excluded_and_incomplete(client):
    assert client.get("/api/outfits/generate").json()["outfits"] == []         # empty wardrobe
    items = basic_wardrobe(client)
    for i in items:
        if i["category"] == "shoes":
            client.patch(f"/api/items/{i['id']}", json={"status": "laundry"})
    r = client.get("/api/outfits/generate").json()
    assert r["outfits"] == [] and "shoes" in r["message"]
    shoes = [i for i in items if i["category"] == "shoes"][0]
    client.patch(f"/api/items/{shoes['id']}", json={"status": "available"})
    for o in client.get("/api/outfits/generate?count=5").json()["outfits"]:
        assert all(i["status"] == "available" for i in o["items"])

def test_dress_outfit_and_accessories(client):
    add(client, "Black dress", "dresses", primary_color="black")
    add(client, "Heels", "shoes", primary_color="black")
    add(client, "Silver watch", "watches", primary_color="silver")
    add(client, "Tan bag", "bags", primary_color="tan")
    o = client.get("/api/outfits/generate").json()["outfits"][0]
    assert {i["category"] for i in o["items"]} == {"dresses", "shoes", "watches", "bags"}

def test_save_replace_and_retrieve_outfit(client):
    items = basic_wardrobe(client)
    o = client.get("/api/outfits/generate?seed=3").json()["outfits"][0]
    saved = client.post("/api/outfits", json={"item_ids": o["item_ids"], "score": o["score"], "reason": o["reason"], "name": "Mine"}).json()
    assert saved["name"] == "Mine" and saved["item_ids"] == o["item_ids"]
    assert client.post("/api/outfits", json={"item_ids": o["item_ids"]}).json()["id"] == saved["id"]   # dedupe
    shoe = next(i for i in saved["items"] if i["category"] == "shoes")
    alts = client.post("/api/outfits/alternatives", json={"item_ids": saved["item_ids"], "replace_id": shoe["id"]}).json()["alternatives"]
    assert alts and all(a["item"]["category"] == "shoes" and a["item"]["id"] != shoe["id"] for a in alts)
    new_ids = alts[0]["item_ids"]
    ev = client.post("/api/outfits/evaluate", json={"item_ids": new_ids}).json()
    assert alts[0]["item"]["id"] in ev["item_ids"] and shoe["id"] not in ev["item_ids"]
    upd = client.patch(f"/api/outfits/{saved['id']}", json={"item_ids": new_ids, "notes": "n", "favorite": True}).json()
    assert alts[0]["item"]["id"] in upd["item_ids"] and upd["favorite"] and upd["notes"] == "n"
    assert len(client.get("/api/outfits").json()) == 1
    assert client.post("/api/outfits", json={"item_ids": [items[0]["id"], items[0]["id"]]}).status_code == 422
    assert client.post("/api/outfits", json={"item_ids": [items[0]["id"], 9999]}).status_code == 422
    assert client.delete(f"/api/outfits/{saved['id']}").status_code == 204

def test_deleting_item_removes_broken_outfit(client):
    items = basic_wardrobe(client)
    o = client.post("/api/outfits", json={"item_ids": [items[0]["id"], items[1]["id"]]}).json()
    client.delete(f"/api/items/{items[0]['id']}")
    assert client.get(f"/api/outfits/{o['id']}").status_code == 404

def test_calendar_history_and_repeats(client):
    items = basic_wardrobe(client)
    o = client.post("/api/outfits", json={"item_ids": [items[0]["id"], items[1]["id"], items[2]["id"]]}).json()
    p = client.post("/api/calendar", json={"date": "2099-01-05", "outfit_id": o["id"]}).json()
    assert not p["worn"]
    assert client.patch(f"/api/calendar/{p['id']}", json={"worn": True}).json()["worn"]
    assert client.post("/api/calendar", json={"date": "nope", "outfit_id": o["id"]}).status_code == 422
    assert client.post("/api/calendar", json={"date": "2099-01-05", "outfit_id": 999}).status_code == 404
    assert len(client.get("/api/calendar?start=2099-01-01&end=2099-01-07").json()) == 1
    from datetime import date, timedelta
    client.post(f"/api/outfits/{o['id']}/wear", json={"date": (date.today() - timedelta(days=3)).isoformat()})
    client.post(f"/api/outfits/{o['id']}/wear", json={})
    h = client.get("/api/history?days=30").json()
    assert len(h["entries"]) == 2 and h["entries"][0]["repeat_of"] is not None
    worn_ids = {i["id"] for i in h["rotation"]["not_worn_recently"]}
    assert items[0]["id"] not in worn_ids and items[3]["id"] in worn_ids      # unworn tee suggested
    assert client.get(f"/api/items/{items[0]['id']}").json()["wear_count"] == 3     # 2099 entry counts as worn=True too

def test_reject_feedback_excludes_combo(client):
    add(client, "Tee", "tshirts", primary_color="black")
    add(client, "Jeans", "jeans_shorts", primary_color="denim")
    add(client, "Shoes", "shoes", primary_color="white")
    o = client.get("/api/outfits/generate").json()["outfits"][0]
    client.post("/api/feedback", json={"item_ids": o["item_ids"], "action": "reject"})
    r = client.get("/api/outfits/generate").json()
    assert r["outfits"] == [] and "seen every" in r["message"]

def test_ssrf_blocked(client):
    for url in ("http://127.0.0.1/", "http://localhost:8000/x", "http://169.254.169.254/latest", "file:///etc/passwd", "ftp://example.com/x", "http://10.0.0.5/"):
        r = client.post("/api/import-url", json={"url": url}).json()
        assert r["ok"] is False and r["error"], url

def test_import_parses_metadata(client, monkeypatch):
    from app import importer
    html = b'<html><head><meta property="og:title" content="Linen Shirt"><meta property="og:image" content="/i.png"></head></html>'
    monkeypatch.setattr(importer, "fetch", lambda url, limit: (html, url) if limit == importer.MAX_HTML else (png((10, 10, 10)), url))
    r = client.post("/api/import-url", json={"url": "https://shop.example/p"}).json()
    assert r["ok"] and r["fields"]["name"] == "Linen Shirt" and r["image"] and r["suggested_color"] == "black"
    monkeypatch.setattr(importer, "fetch", lambda url, limit: (b"<html></html>", url))
    r = client.post("/api/import-url", json={"url": "https://shop.example/p"}).json()
    assert r["ok"] is False and "manually" in r["error"]

def test_preferences_categories_demo_export_delete(client):
    assert client.put("/api/preferences", json={"favorite_colors": ["navy"], "onboarded": True}).json()["favorite_colors"] == ["navy"]
    assert client.put("/api/preferences", json={"nope": 1}).status_code == 422
    assert client.put("/api/preferences", json={"favorite_colors": "navy"}).status_code == 422
    assert client.post("/api/categories", json={"id": "hats", "label": "Hats", "slot": "accessory"}).status_code == 201
    assert client.post("/api/categories", json={"id": "hats", "label": "Hats", "slot": "accessory"}).status_code == 409
    add(client, "My real tee", "tshirts")
    assert client.post("/api/demo").json()["added"] > 10
    assert client.post("/api/demo").status_code == 409
    o = client.get("/api/outfits/generate?occasion=work&season=spring").json()
    assert o["outfits"] and all(i["is_demo"] for i in o["outfits"][0]["items"] if i["name"] != "My real tee")
    assert client.get("/api/export").json()["items"]
    z = zipfile.ZipFile(io.BytesIO(client.get("/api/export/backup").content))
    assert "oftly.db" in z.namelist() and any(n.startswith("media/") for n in z.namelist())
    assert client.delete("/api/demo").json()["removed"] > 10
    assert client.get("/api/summary").json()["total"] == 1                     # real item kept
    assert client.delete("/api/data").status_code == 400
    assert client.delete("/api/data?confirm=true").status_code == 200
    assert client.get("/api/summary").json()["total"] == 0
