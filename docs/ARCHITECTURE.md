# Architecture

```
frontend/  index.html, styles.css, app.js     plain JS single-page app (hash routes), served by the backend
backend/app/
  main.py      FastAPI routes (items, outfits, calendar, history, prefs, export, demo)
  models.py    Pydantic validation
  db.py        SQLite connection + versioned migrations (MIGRATIONS list) + default categories
  engine.py    outfit generation, scoring, alternatives (pure functions, no I/O)
  images.py    upload validation, JPEG re-encode, dominant colour suggestion
  importer.py  product URL import with SSRF protections
  demo.py      generated demo illustrations + demo item list
data/          veya.db and media/ (created at runtime, git-ignored)
tests/         pytest: API + engine
```

## Why these choices
* **FastAPI** – typed validation, automatic API docs at `/docs`. **SQLite** – zero setup, one file to back up.
* **Pillow** – decoding/re-encoding uploads (strips risky formats and metadata) and colour extraction. **httpx** – URL import with manual redirect handling.
* **No build step** – a beginner can run the app with Python alone. Trade-off: not React/TypeScript. Moving to Vite/React would only
  touch `frontend/`; the API is stable JSON.

## Data model
`categories(id,label,slot)` · `items` · `outfits` · `outfit_items` · `calendar(date,outfit_id,worn)` · `feedback(signature,action)` · `preferences(key,value JSON)`.
Wear history = calendar rows with `worn=1`. A category's **slot** (top, bottom, dress, shoes, bag, accessory) tells the engine how to use it;
add categories with `POST /api/categories`. Multi-user readiness: add a `user_id` column per table in a new migration.

## Recommendation engine
Templates: top + bottom + shoes, or dress + shoes, plus up to two accessories (one bag, one per accessory category). Only `available` items are used; no item appears twice.
Score (0-100) = weighted mean of: colour harmony 40 (neutrals, analogous, complementary; penalties for two patterns or 3+ accent colours),
formality consistency/target 20, occasion 15, season 10, user preferences 10, freshness (time since worn) 5 — components that don't apply are dropped.
Small bonus for favourites; −15 if the same outfit was worn in the last 14 days. Results are diversified (differ in ≥2 pieces when possible),
skip combinations you rejected, and the score breakdown is returned by the API. Swapping uses `/api/outfits/alternatives` and `/api/outfits/evaluate`.

## Privacy and security
Local-first: data and photos stay in `data/`; the server binds to 127.0.0.1; no analytics; no third-party calls except the URL import you trigger.
Uploads: size cap 8 MB, JPEG/PNG/WebP only, verified and re-encoded, random filenames, pixel limit; `/media/<name>` accepts only a strict filename pattern.
URL import: http(s) only, ports 80/443, resolved addresses must be public, re-validated on each redirect, 6 s timeout, size caps.
Known gaps: DNS-rebinding between check and connect is not fully prevented; **there is no authentication**. For any shared or public deployment you need
authentication, per-user data separation, HTTPS, rate limiting, CSRF protection, and stricter outbound-fetch isolation. Do not expose this server to the internet as is.
Uploads that are never attached to an item stay in `data/media/` until you delete all data.

## Testing
`pytest` covers: item CRUD, validation, uploads/serving/traversal, filters/search/sort/pagination, outfit generation, unavailable/empty/incomplete wardrobes,
scoring rules, saving, swapping, calendar and history, feedback, SSRF blocking, import parsing (network mocked), preferences, categories, demo, export/backup, deletion.
The frontend has no automated tests in the shipped project.
