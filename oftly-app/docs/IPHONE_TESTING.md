# Testing OFTLY on your own iPhone

**Route chosen: the web app (PWA-style), over HTTPS.** OFTLY is a FastAPI + web UI project. A native iOS app does not exist (an old Expo prototype is in git history, unmaintained), and building one would mean a rewrite plus Apple fees. The web app installs to the Home Screen from Safari, runs full-screen, supports camera/photo upload and keeps you signed in. Native/TestFlight is a later decision (see `docs/LAUNCH_CHECKLIST.md`).

> **Honesty note.** I (the build assistant) tested in desktop headless Chrome at iPhone-sized viewports. I could **not** test on a real iPhone, Safari/WebKit or iOS. Everything in "Your device checklist" below is yours to verify.

## What you need
- Your MacBook (any recent macOS) with Terminal, Python 3.10+ (`python3 --version`) and [Homebrew](https://brew.sh).
- Your iPhone and the same Wi-Fi (not required by the tunnel, but handy).
- **No Apple Developer account, no cost.**

## Option A (recommended now): private HTTPS link from your Mac via Cloudflare quick tunnel
1. Open Terminal and install the tunnel tool once: `brew install cloudflared`
2. Unzip the project, then: `cd ~/Downloads/oftly-app && chmod +x scripts/*.sh && ./scripts/beta.sh`
3. After ~20 seconds the Terminal prints a box with **an `https://…trycloudflare.com` address and an invite code**. Keep that window open and your Mac awake (System Settings → Lock Screen / Battery → prevent sleep while testing).
4. On the iPhone, open the address in **Safari** (not an in-app browser). Register with the invite code.
5. **Add to Home Screen:** tap Share (square with arrow) → *Add to Home Screen* → *Add*. Open OFTLY from the new icon.
6. Stop the beta: press **Ctrl+C** in Terminal. The link dies; a new run gives a **new address** (re-add to Home Screen, sign in again).
Data lives in `data-beta/` (separate from normal local data). It stays after Ctrl+C.

*Not verified by me:* `scripts/beta.sh` and the tunnel (the build sandbox has no access to Cloudflare). If something fails, see Troubleshooting. The app side (invite codes, Secure cookies, host allow-list, proxy headers) is covered by automated tests.

## Option B: always-on hosted HTTPS (later)
`Dockerfile`, `docker-compose.yml` and `Caddyfile` run OFTLY on a small server with an automatic certificate for your own domain. Untested in the sandbox. Needs a server, a domain, and `.env` (see `.env.example`). Choose this when friends need access while your Mac is off.

## Option C (not recommended): same-Wi-Fi plain HTTP
Works for layout checks only: no HTTPS means Secure cookies don't work and sign-in would fail. Skip.

## Troubleshooting
| Symptom | Fix |
|---|---|
| "Unrecognised host" (HTTP 400) | The tunnel address changed. Re-run `./scripts/beta.sh` (it sets `OFTLY_ALLOWED_HOSTS` for the new address). |
| Sign-in loops / "Security check failed" | Delete the old Home Screen icon and website data (Settings → Safari → Advanced → Website Data), then use the new address. |
| Safari says the page can't be opened | Tunnel not running, Mac asleep, or old address. Re-run the script. |
| Photo upload does nothing | Settings → Safari → Camera / Photos permissions; photos must be < 10 MB (HEIC from the camera is converted). |
| Not signed in after reopening the Home Screen app | iOS can clear web-app storage if the app is unused for a long time. Sign in again (your data is on the server). |
| `brew: command not found` | Install Homebrew from brew.sh, then retry. |
| Forgot password, no email | Email isn't configured. Run `cd backend && ../.venv/bin/python -m app.admin reset-link friend@example.com` and send them the link. |

## Your device checklist (only you can do these on a real iPhone)
Sign-up with invite code · walkthrough (accessibility step first, then 3 steps; Back/Next/Skip) · skip works · Settings → Replay walkthrough · Settings → Accessibility opens · change text size / dark / high contrast and confirm they persist after closing and reopening · add an item with camera, then with a library photo (permission prompts appear) · edit/delete an item · generate outfits · swap a piece · save/wear an outfit · destination weather (turn weather on, enter a city; try a nonsense city: expect a clear "no forecast" message, no numbers) · airplane mode: banner + friendly errors, then recovery · sign out, then Back button: you must land on sign-in with no wardrobe visible · sign in again · close and reopen the Home Screen app (still signed in) · rotate device · notch/home-bar overlap (bottom nav sits above the home indicator) · delete the test account.
