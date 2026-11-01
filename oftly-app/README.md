# OFTLY: Your Wardrobe. Reimagined.

OFTLY is a private digital wardrobe and outfit planner: add the clothes you own, get outfit suggestions explained piece by piece, and plan what to wear (optionally around destination weather). Style more, buy less.

**Status: private-beta release candidate (v0.4.0).** Ready for personal iPhone testing and an invite-only friends-and-family beta. **Not ready for public launch**; see `docs/LAUNCH_CHECKLIST.md` and `docs/SECURITY_REPORT.md`.

## Quick start on a Mac (local, beginner steps)
```bash
cd ~/Downloads/oftly-app            # the unzipped folder
chmod +x scripts/*.sh
./scripts/start.sh                  # creates .venv, installs dependencies, starts OFTLY, opens http://127.0.0.1:8000
```
Create an account on the sign-in screen (email + password of 12+ characters). Your first sign-in starts the walkthrough. Stop with **Ctrl+C**. Accounts and photos are stored in `./data/` (never in Git).

## Test on your iPhone and with friends
Read **`docs/IPHONE_TESTING.md`** (step by step) and **`docs/BETA_TESTING.md`** (invites, feedback form, device checklist). Short version: `brew install cloudflared`, then `./scripts/beta.sh` prints an HTTPS link and an invite code; open the link in Safari and *Add to Home Screen*.

## Tests
```bash
./scripts/test.sh                       # or: .venv/bin/python -m pytest -q      (backend, security, isolation, branding)
# real-browser + accessibility suite (Node 18+, Chrome):  see tests/frontend/package.json and docs/TEST_RESULTS.md
```
Results of the last full run, and what was *not* verified, are in `docs/TEST_RESULTS.md`.

## Configuration (all optional; see `.env.example`)
`OFTLY_PORT`, `OFTLY_DATA`, `OFTLY_INVITE_CODES`, `OFTLY_PUBLIC_URL`, `OFTLY_ALLOWED_HOSTS`, `OFTLY_COOKIE_SECURE`, `OFTLY_MAIL` + `OFTLY_SMTP_*`, `OFTLY_MAX_PHOTOS`. Development only: `OFTLY_DEBUG`, `OFTLY_ENABLE_DEMO`. **No API keys or paid services are needed.**

## Operator tools
```bash
cd backend
../.venv/bin/python -m app.admin list-users
../.venv/bin/python -m app.admin reset-link friend@example.com    # helps a tester when email isn't configured
../.venv/bin/python -m app.admin new-invite
../.venv/bin/python -m app.admin delete-user friend@example.com   # removes the account and all its data
```

## Privacy in one paragraph
Each account's wardrobe, photos and preferences are stored in that account's own folder and are only served to that signed-in account. Photos are re-encoded and stripped of location data, and are never sent to any AI service. Weather is off by default and sends only a place name to Open-Meteo when you turn it on. No analytics or ads. Account deletion removes everything immediately. The privacy policy and terms inside the app are **drafts** that need legal review.

## Features
Wardrobe with photos, filters and one-click quick filters · outfit generator with explainable scores (colour, formality, occasion, climate, taste, variety) · piece swapping · saved outfits, wear history and planner · destination and day weather planning (optional, never invented) · insights and wardrobe map · learning from your feedback · accessibility panel with presets for vision, colour vision, reading, movement and comfort · optional local intelligence integration (`docs/INTELLIGENCE_CONTRACT.md`, disabled by default).

## Documentation
`docs/SECURITY_REPORT.md` · `docs/ARCHITECTURE.md` · `docs/ONBOARDING_AND_ACCESSIBILITY.md` · `docs/IPHONE_TESTING.md` · `docs/BETA_TESTING.md` · `docs/LAUNCH_CHECKLIST.md` · `docs/TEST_RESULTS.md` · `docs/CHANGELOG.md` · `docs/HANDOVER_LOG.md` · `docs/INTELLIGENCE_CONTRACT.md` · `docs/DATASET_PLAN.md` (datasets/models: nothing downloaded or trained).

Fonts (Fraunces, Instrument Sans, Atkinson Hyperlegible) are bundled under the SIL Open Font License (`frontend/fonts/`).
