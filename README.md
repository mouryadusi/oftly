# Veya — Your Wardrobe. Reimagined.
*Style More. Buy Less.*

Veya is a local-first digital wardrobe. Catalogue what you own (photo, upload, product link or manual entry) and Veya
suggests outfits from those clothes only, using a transparent rule-based engine. No AI APIs, no accounts, no tracking.

## Install and run on a Mac (beginner steps)

1. **Check Python 3.10+.** Open *Terminal* (Cmd+Space, type "Terminal") and run `python3 --version`.
   If it is missing or older, install it from https://www.python.org/downloads/ (or `brew install python`).
2. **Unzip** `veya-wardrobe-app.zip` (double-click it), then in Terminal:
   ```bash
   cd ~/Downloads/veya-wardrobe-app      # adjust if you unzipped elsewhere
   ./scripts/start.sh
   ```
   If macOS says permission denied, run `chmod +x scripts/*.sh` once and retry.
   The first run creates `.venv`, installs dependencies (internet needed once), creates the database, and opens
   http://127.0.0.1:8000 in your browser.
3. On the welcome screen choose **Try the demo wardrobe** or **Add my first item**.
4. **Stop:** press `Ctrl+C` in the Terminal window (or run `./scripts/stop.sh` from another window).

### Manual steps (what start.sh does)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000
```
The database (`data/veya.db`) is created automatically on startup. There is no separate frontend build: the
frontend is plain HTML/CSS/JS served by the backend, so Node.js is **not** needed.

## Tests
```bash
./scripts/test.sh          # or: source .venv/bin/activate && python -m pytest -q
```

## Your data
* Everything lives in `data/` (database `veya.db`, photos in `data/media/`).
* **Backup:** Settings → *Backup* downloads a ZIP of the database and photos, or run `./scripts/backup.sh`.
* **Export:** Settings → *Export data (JSON)*. **Restore:** stop Veya, put `veya.db` and `media/` from a backup into `data/`.
* **Demo data:** Settings → *Remove demo items* removes only demo items (marked "Demo"). *Delete all my data* wipes everything.
* API documentation: http://127.0.0.1:8000/docs

## Troubleshooting
| Problem | Fix |
|---|---|
| `command not found: python3` | Install Python from python.org, reopen Terminal |
| `Address already in use` | Run `./scripts/stop.sh`, or set `VEYA_PORT=8001` in `.env` (copy `.env.example`) |
| `pip install` fails | Check your internet connection; upgrade pip: `.venv/bin/pip install -U pip` |
| Blank page / "Can't reach backend" | Make sure the Terminal window running start.sh is still open |
| Product import says it failed | Many shops block automatic access. Enter the details manually and upload a photo |
| Camera button does nothing on desktop | "Take photo" works on phones/tablets; use *Upload photo* on a Mac |

## Features
Onboarding · Today's outfit with alternatives, regenerate, save, reject ("Not for me") · searchable/filterable wardrobe
with category pages · add/edit/delete items (photo upload, camera on mobile, URL import, manual) · per-item swap inside
an outfit · saved outfits with notes · weekly planner, worn history, repeat warnings, rotation suggestions · preferences ·
export/backup/delete · demo wardrobe.

## Known limitations (MVP)
* Frontend is **vanilla JavaScript**, not React/TypeScript, and there are no automated browser tests (see docs/ARCHITECTURE.md).
* No in-app image cropping (replace the photo instead). Colour detection is a simple Pillow-based suggestion; OpenCV is not used.
* No machine-learning model is bundled; see docs/ML_INTEGRATION.md and docs/MODELS_AND_LICENSES.md.
* No weather integration (and no fake weather).
* Single local user. Not hardened for public deployment (see docs/ARCHITECTURE.md → Privacy and security).
* No share image export; use *Copy summary* on a saved outfit.
