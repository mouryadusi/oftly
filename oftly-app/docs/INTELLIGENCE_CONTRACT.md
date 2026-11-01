# OFTLY INTELLIGENCE integration contract: `oftly.intelligence/1`

OFTLY's core never imports a model. It calls an optional **provider** over a tiny HTTP contract. Default: no provider; the deterministic engine runs alone.
Code: `backend/app/intelligence/` · Dev stub: `scripts/stub_intelligence.py` · Tests: `tests/test_v2.py` (intelligence section).

## Enable
`OFTLY_INTELLIGENCE_URL=http://127.0.0.1:9911 ./scripts/start.sh` – the URL **must** be `http://` + loopback (`localhost`, `127.0.0.0/8`, `::1`), no credentials; anything else is ignored with a message at `GET /api/intelligence/status`.

## Guarantees OFTLY enforces (the provider cannot weaken these)
- Timeout 3 s per call; response ≤ 1 MB; no redirects; circuit breaker (3 failures → paused 60 s). A dead/slow/hostile provider never breaks the app.
- Score nudges bounded to **±8**; out-of-range or malformed entries are **dropped**, not clamped; unknown ids ignored; notes ≤ 200 chars.
- Applied nudges are reported separately (`adjustments.intelligence`) and shown in the UI; the built-in score is never hidden.
- Suggestions are **never written** to confirmed item fields; they return with `confirmed:false` and the user decides.
- Ranking requests contain only ids and attributes (no names, notes, brands, prices or photos).

## Endpoints the provider implements
`GET /v1/health` → `{"name","version","capabilities":["rank_outfits","suggest_attributes"]}`

`POST /v1/rank_outfits`
```json
{"contract":"oftly.intelligence/1",
 "context":{"occasion":"work","climate_band":"autumn","temp_c":14,"rain_chance":60,"favorite_colors":["navy"],"disliked_colors":["yellow"]},
 "outfits":[{"id":"1-8-15","base_score":84.2,"pieces":[{"id":1,"slot":"top","category":"shirts","colour":"white","pattern":"solid","style":"classic","formality":3}]}]}
```
→ `{"adjustments":[{"id":"1-8-15","delta":2.5,"note":"Echoes a look you wore and liked"}]}`

`POST /v1/suggest_attributes` (multipart `image`, JPEG/PNG/WebP ≤ 8 MB) → `{"suggestions":[{"field":"category","value":"shirts","confidence":0.82}]}`
OFTLY exposes these at `GET /api/items/{id}/suggestions` (labelled as suggestions).

## Versioning
Breaking changes bump the contract string (`/2`); OFTLY sends `contract` in every request. Additive fields are ignored by older sides.

## Verified so far
Unit-tested with fake transports (bounds, malformed/hostile replies, breaker, loopback enforcement, data minimisation) and run once end-to-end against `scripts/stub_intelligence.py` over real HTTP. **No real intelligence model has been connected.**
