# OFTLY architecture

```
frontend/ (static, no build step)      index.html · styles.css · a11y.css · a11y.js · fx.js · ui-auth.js · app.js · manifest.webmanifest · icons/ · fonts/
backend/app/
  main.py        routes (wardrobe, outfits, planner, insights, weather, export); middleware stack; serves the frontend
  auth.py        accounts DB, Argon2id, sessions, CSRF, rate limits, recovery, deletion, AuthGuard middleware
  security.py    LocalGuard (host/origin/headers/HSTS) and BodyLimit (request size)
  config.py      env settings and the per-request user context (selects the account's data folder)
  db.py          per-account SQLite schema + migrations (created on first use)
  engine.py / stylist.py / weather.py / images.py / importer.py   recommendation, narration, forecast, uploads, product import
  intelligence/  optional, loopback-only provider boundary (contract oftly.intelligence/1)
  admin.py       operator CLI
data/            accounts.db · users/<uuid>/oftly.db · users/<uuid>/media/*.jpg      (git-ignored)
tests/           pytest (backend, security, isolation, branding) · tests/frontend (real-browser + axe)
```
**Request path:** `LocalGuard → BodyLimit → AuthGuard → route`. AuthGuard resolves the session cookie (or Bearer token), enforces the CSRF header on state-changing calls, then sets the user context so `db.conn()` and `media_dir()` can only open **that account's** files. Routes outside `/api/auth/*`, `/api/health`, `/api/engine` and the static frontend return 401 without a session.
**Why SQLite per account:** isolation by construction and zero-ops for a small beta. Trade-offs (scale, backups, cross-account analytics) are in `SECURITY_REPORT.md` §3 and `LAUNCH_CHECKLIST.md`.
**Offline / failure behaviour:** network errors become a clear message and a banner; weather or intelligence failures degrade to the deterministic engine and never fabricate data.
**Mobile:** installable web app today (manifest, Home-Screen icons, safe areas). A native app is not started; a Capacitor wrap of this UI is the suggested first step (needs hosted HTTPS and an Apple Developer account).
