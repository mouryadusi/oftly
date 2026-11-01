# OFTLY handover log

Rule: an entry says "done" only if it was actually done and checked. "Unverified" means exactly that.

## 2026-10-22 — Reconciliation (Account 1, lead developer)

**Verified (by running commands):**
- GitHub `main` (27262fe "Replace app with local-first wardrobe app") is the **FastAPI + SQLite + Pillow + vanilla JS** app.
  `diff -rq` of the original `oftly-wardrobe-app.zip` against `main` shows **no differences**.
- ZIP SHA-256 = `66f34384d59b352cd1bb42f4f5ad7aba8b4e2faec234c6d21bd141d4611bb4f0` (matches the reported hash).
- The Expo/React Native + Supabase + OpenAI app is the **first commit 80c0d0e** ("Initial OFTLY app"), later replaced.
  The second account most likely read that older commit/cached view. There is one codebase on `main`, not two.
- `pytest`: **21 passed** (Python 3.12, fresh venv, Linux sandbox). Not yet run on macOS. No real-browser test exists.
- No OpenAI/Gemini/Supabase references remain at `main`. In 80c0d0e, OpenAI (`gpt-4o-mini`, 9 references) was used in six
  Supabase edge functions: analyze-garment, analyze-wardrobe-photo, extract-product, outfit-followup, recommend-outfit,
  wardrobe-insight. History scan found only placeholder keys (`sk-...`), no real secrets.

**Decisions:**
1. `main` is the base. The Expo/Supabase app is archived, not merged. Suggested: `git tag archive/expo-supabase 80c0d0e`.
2. Exposed-in-history item to review: a Supabase project ref appears in old HANDOVER.md. It is an identifier, not a key, but rotate/disable that project if unused.
3. No ML is added until the dataset/model gates in docs/DATASET_PLAN.md pass.

**Outstanding:** UI redesign (editorial/immersive), accessibility settings, weather (optional, graceful fallback), local vision module,
browser tests, macOS run check, verifying unverified licences.

## 2026-10-22 — Stylist intelligence pass (Account 1)

**Implemented and tested (pytest 37 passed; jsdom DOM smoke 17/17, run against a live local server):**
- `backend/app/stylist.py`: grounded outfit narration (editorial title, intention, per-piece notes, colour story, focal point,
  practical notes, "why this works for you", score factors). Uses only recorded attributes; metals on accessories read as a finish,
  not an accent colour; explicit `not_assessed` (fit/silhouette, fabric/warmth/breathability).
- Feedback learning (`engine.learn`): 30-day half-life, one rejection is gentle, exact combo re-allowed after 14 days, wear/like add signal.
  Adjustments (`learned`, `avoided_colour`) are reported beside the score.
- Profile prefs: preferred_name, gender (optional, inclusive), city, use_weather (off by default), fit, disliked_colors; validated.
- `backend/app/weather.py` (Open-Meteo, opt-in, fixed hosts, no redirects, 6 s timeout, size cap, never fabricates).
- Frontend: personalised greeting, outfit reasoning UI, name in onboarding, profile + accessibility settings (dark, text size, high contrast,
  reduced motion, larger targets), skip link, Help/Privacy/Terms(draft)/Community/Get-the-app pages written to match the local app.

**NOT verified:** Open-Meteo live calls (sandbox network blocked; tested only with mocked responses); real-browser rendering, dark/high-contrast
visuals, contrast ratios, screen-reader behaviour, touch, iOS Simulator, macOS run.

**Not built (decisions needed):** accounts/login/password recovery (app is single-user local; auth without per-user data isolation would be
cosmetic: needs a decision to go multi-user), Contact page (needs a real delivery channel from you; none invented), camera/"photo" styling
dimension, impression selector UI (engine supports `impression`), PWA/offline, local vision module (awaiting dataset/model approval), URL-import
improvements, Expo evaluation, App Store docs.

## 2026-10-23: v0.3.0 (Account 1, lead developer)
**Done and verified by running it**
- Backend: 59 pytest tests pass (Linux, Python 3.12), incl. destination weather (fake transport), climate scoring, graceful weather failure, loopback/Origin guards (with a mutation check proving the test can fail), EXIF/GPS stripping, insights, filters, intelligence bounds/hostile-provider handling.
- Browser: real headless Chrome 153 (Linux) via puppeteer-core: functional flows, accessibility presets (computed styles checked), keyboard, overflow at 320/390/768/1024/1440 px, and axe-core WCAG A/AA audits (see TEST_RESULTS.md for the final tally of the last run).
- Intelligence stub run end-to-end over real HTTP.
**Not verified**: real Open-Meteo (sandbox cannot reach it; fake used), macOS/Safari/iOS, real users with the conditions the presets target, colour-vision presets against real CVD simulation, screen readers (VoiceOver/NVDA). axe finds only automatable issues.
**Decisions**: auth deliberately deferred (docs/SECURITY_AND_MOBILE_AUTH.md); Capacitor-before-React-Native recommended; datasets/models unchanged (docs/DATASET_PLAN.md: nothing downloaded, nothing trained).
**Blocked on owner**: hosting model, email provider for password recovery, legal entity/contact for privacy policy and App Store, approval to download any dataset.
**Reference-site caveat**: only page HTML was read; scroll/WebGL behaviour of the five sites was not observable, so the interactions are original implementations of the *patterns* (ticker, slider, preloader counter, numbered sections, discovery map).

## 2026-10-26: v0.4.0 OFTLY private-beta RC
Renamed to OFTLY (mark reworked to an O-ring; palette kept). Added full authentication (Argon2id, hashed server-side sessions, CSRF, rate limits, recovery, deletion, invite codes) with **per-account databases and photo folders**; first-run flow (accessibility step + 3-step walkthrough); accessibility panel moved off the home screen; demo content removed from the product (tests only); installable iPhone web app, offline states, beta tunnel script. Verified: 96 backend tests, 80 real-browser checks incl. 39 axe audits (chunked runs). **Unverified: real iPhone/Safari, tunnel script, SMTP, real HTTPS, VoiceOver.** Docs: SECURITY_REPORT, IPHONE_TESTING, BETA_TESTING, LAUNCH_CHECKLIST, TEST_RESULTS, STATUS.
**Owner actions needed:** run `scripts/beta.sh` and the device checklist; choose hosting/mail provider/legal entity; commission an independent security review; approve any dataset downloads (none done). Old ZIPs/patches moved to `outputs/archive/`.
