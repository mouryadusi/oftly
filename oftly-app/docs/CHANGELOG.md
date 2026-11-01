# Changelog

## v0.4.0: OFTLY private-beta release candidate (app renamed from "Veya")
**Renamed** the app to **OFTLY** everywhere (UI, titles, manifest, docs, env vars `OFTLY_*`, tests). The wardrobe-neckline mark was reworked into an **O-ring + clay neckline** because the old "V" mark no longer matched the name; palette, typography and layout are unchanged. Guarded by `tests/test_branding.py`.
**Security / accounts (new)**: registration, login, logout, logout-everywhere, change password, password recovery (hashed single-use 30-min tokens; SMTP or operator CLI), account deletion; Argon2id hashing; server-side sessions (HttpOnly cookie, hashed at rest, idle 7d / absolute 30d, revocable); CSRF double-submit; per-IP and per-account rate limits + lockout; invite codes for the private beta; **per-account database and photo folder** (structural data isolation); body-size limits, per-user photo quota, EXIF/GPS stripping verified; HSTS over HTTPS; docs endpoints off by default; generic error responses. `python -m app.admin` operator tools. See `docs/SECURITY_REPORT.md`.
**Onboarding**: first-run flow = optional accessibility step, then a 3-step walkthrough (Build / Discover / Plan) with Back, Next, Skip and Finish; shown once per account; replayable from Settings.
**Accessibility**: the floating Accessibility button is gone; the panel opens from onboarding, Settings → Accessibility, the sign-in pages and Alt+A. Preferences persist on the device.
**Clean test environment**: demo/sample garments removed from the user experience (endpoints disabled unless `OFTLY_ENABLE_DEMO=1`, used only by automated tests); new accounts start with an empty wardrobe.
**iPhone**: installable web app (manifest, Home-Screen icons, safe-area handling, 16px inputs), offline banner and friendly network errors, `scripts/beta.sh` (HTTPS tunnel), `Dockerfile`/Caddy for hosting (untested here).
**Fixed (found by the browser tests)**: a stylesheet-parsing regression I introduced in `a11y.css`; taps lost for ~0.3 s after navigation caused by view transitions (removed); 320 px overflow on auth pages; carousel/preset timing races in tests.
**Tests**: 100+ backend tests (auth, isolation, uploads, branding, regression) and a real-browser suite with axe-core. See `docs/TEST_RESULTS.md`.

## v0.3.0: editorial redesign, destination weather, accessibility panel, integration boundary
**Added**
- **Editorial UI**: bundled Fraunces / Instrument Sans / Atkinson Hyperlegible (SIL OFL, no CDN), display typography with accent words, preloader counter (first visit only), scroll reveal, parallax, marquee ticker with a Pause control, snap carousels (buttons, arrow keys, optional drag), score ring, factor bars, insights tiles (ring, sparkline, palette strip), Voronoi **wardrobe map**, view transitions between pages, mobile bottom navigation.
- **Destination replaces Season** in the styling flow: destination + day (today to +6) → temperature, rain, humidity, wind from Open-Meteo (opt-in; only the place name is sent). Item climate tags (winter/autumn/spring/summer = cold/cool/mild/hot) now score against the destination's real temperature band. No weather → no weather claims.
- **Accessibility panel** (Alt+A, button on every page): 17 combinable presets (low vision, cataracts, presbyopia, AMD, visual fatigue, protan/deutan/tritan/achromatopsia, dyslexia, simple & calm, photosensitivity, tremor, Parkinson's, osteoarthritis, night comfort, bright light), temporary presets that auto-revert (1 h / 1 day / 1 week), and fine-tuning for theme (light/dark/warm night), contrast (3 levels), text size (100–175%), line/letter/word spacing, legible typeface, bold, underlined links, screen dimming, animation (reduce/off), tap size, focus outline, steady taps, no-drag, simple view, colour-vision support (CVD-safe interface colours + colour names on garments).
- **One-click wardrobe filters**: Favourites, Not worn in 30 days, Neutrals, Colour, Dressy, Work, In laundry. New API filters `unworn_days`, `palette`, `min_formality`.
- `GET /api/insights` (real records only), `GET /api/weather?destination=&day=`.
- **OFTLY INTELLIGENCE boundary** (`backend/app/intelligence/`, `docs/INTELLIGENCE_CONTRACT.md`, `scripts/stub_intelligence.py`).
- **Local-API hardening** (`security.py`): loopback Host check, cross-site write refusal, strict CSP and headers.
- Richer demo garment illustrations (lighting, shading, seams, shadow); clearly labelled "DEMO · ILLUSTRATION".
- Grounded stylist narration and gradual feedback learning (from v0.2, committed `02c4bd4`).
**Changed**
- Season removed from Today, wardrobe filter bar and settings (API `season` parameter still accepted for compatibility; ignored when destination weather is available).
- Initial page load no longer moves focus into `<main>`, so the skip link is the first Tab stop.
**Fixed** (found by the browser tests)
- Mobile bottom navigation rendered at the top (header `backdrop-filter` trapped `position:fixed`).
- 541 px horizontal overflow at 390 px (map min-height forced width).
- Staggered outfit pieces overlapped captions.
**Removed**: the old jsdom smoke test (replaced by real-browser tests).
