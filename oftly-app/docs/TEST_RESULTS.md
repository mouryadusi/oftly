# Test results: OFTLY v0.4.0 release candidate

**Environment:** Linux sandbox VM (Python 3.12, Node 22, headless **desktop Chrome 153** via puppeteer-core, axe-core 4.x). **Not run on a real iPhone, Safari/WebKit, iOS, or macOS.** Weather in browser tests is a **fake Open-Meteo** (the sandbox cannot reach the real one). Password-reset email and the HTTPS tunnel/hosting scripts could not be exercised.

## 1. Backend: `python -m pytest -q` → **96 passed, 0 failed**
| Area | Count | Highlights |
|---|---|---|
| Authentication, sessions, CSRF, rate limits, recovery, deletion, uploads, isolation, headers | 34 | every API route returns 401 anonymously (all 39 method/route pairs + media); two-account isolation of items/outfits/preferences/photos/exports/wipe; path traversal; brute-force lockout survives a limiter reset; single-use hashed reset tokens; password never in logs |
| Destination weather, climate scoring, local guards, insights, intelligence boundary, EXIF/GPS stripping | 23 | host/origin guards, hostile intelligence provider, graceful weather failure |
| Stylist, feedback learning, original regression suite | 36 | the original 21 regression tests still pass unchanged under authentication |
| Branding (old name absent from code/UI/docs/config; manifest, icons, title) | 3 | |
**Mutation checks:** deliberately breaking user isolation made the isolation and deletion tests fail; removing the host guard made the DNS-rebinding test fail. **Dependency scan:** `pip-audit -r requirements.txt` → no known vulnerabilities (run at build time; repeat before launch).

## 2. Real browser: `tests/frontend/run_e2e.sh` → **80 checks, 80 passed, 0 failed**
Run on the final application code in **six separate runs** (the sandbox VM restarts every ~15–20 minutes, which killed longer continuous runs, so I could not produce one uninterrupted pass; each chunk used a fresh seeded server). One chunk was re-run after the VM restart interrupted it.
- **Today & wardrobe (13):** no console/CSP errors, bundled fonts with zero external requests, personalised greeting, Season removed / Destination + When present, destination "Oslo / Tomorrow" calls API with both, unknown place shows no invented numbers, promote alternative, copy summary, insights + map, carousel buttons and arrow keys, marquee pause, one-click filters match the API.
- **Accounts & onboarding (11):** signed-out visitor → sign-in with nav hidden and APIs 401; wrong password → one generic error; registration → accessibility step first → three steps with Back/Next/Skip/Finish → clean empty wardrobe, no demo/sample text; walkthrough does not return after reload; session cookie HttpOnly + SameSite=Lax and unreadable by scripts; CSP/frame headers; new account cannot see another account's items; Settings → replay walkthrough, reopen accessibility, sign out (Back button cannot reveal data); sign back in, session survives reload; delete account with wrong then right password and the deleted account cannot sign in; forgot-password honest/generic; **offline banner and friendly failure then recovery**; old name absent on 11 pages, manifest/icons OFTLY; user-entered HTML shown as text; auth pages without overflow at 320/390/768 and dark mode.
- **Accessibility behaviour & layout (17):** Alt+A and Esc, no permanent accessibility button, presets (dyslexia, presbyopia combined, tremor incl. steady taps, photosensitivity, low vision, protanopia), dark + dim, persistence and reset, temporary preset expiry, skip-link first Tab stop, **no horizontal overflow at 1440/1024/768/390/320 px**, mobile nav ≥44 px.
- **axe-core WCAG 2.0/2.1/2.2 A+AA (39 audits, 0 violations):** signed-in Today, Wardrobe, Settings, Help and walkthrough in light, dark, warm night, high contrast, maximum contrast, and legible font at 150 % (30); signed-out sign-in, register and recovery in light, dark and maximum contrast (9).

## 3. Defects found and fixed during this round
Critical/high (all fixed and covered): accessibility stylesheet silently broken by my own cleanup (all accessibility presets non-functional) · **taps lost for ~0.3 s after every navigation** (page-transition API; removed) · 320 px overflow from the bottom nav and from outfit-collage captions (iPhone SE-class widths) · sticky header could obscure scroll targets (WCAG focus-obscured) · login/register form overflow at 320 px · old "V" mark inconsistent with the new name (replaced).
Test-harness issues (not product defects): shared cookie jar made "anonymous" tests signed in; fixed waits/races on hash navigation, sign-in and rate-limited calls.

## 4. Remaining issues (not fixed) and what was NOT verified
- **No real iPhone / Safari / iOS testing.** Everything about touch, camera/photo permissions, Home-Screen behaviour, safe areas on a real notch, and Safari quirks is unverified. You must run the checklist in `docs/IPHONE_TESTING.md`.
- `scripts/beta.sh` (Cloudflare tunnel), `Dockerfile`, `docker-compose.yml`, `Caddyfile` and SMTP email delivery were **written but never executed**.
- Secure-cookie/HSTS behaviour verified with simulated HTTPS headers only, not a real certificate.
- No screen-reader (VoiceOver/NVDA) testing; axe catches only automatable issues. No load or soak testing. No independent penetration test.
- Medium/low: no email verification; registration reveals existing emails (409); in-memory rate limiter; CSP permits inline styles; logo is a competent placeholder, not a professional identity; privacy policy/terms are drafts; Open-Meteo live response parsing unverified (fake used); demo-illustration generator remains in code for tests only.
- Browser suite could not be executed as one continuous run (VM restarts).
Screenshots of the final build: `docs/screenshots/`.
