"""The app is named OFTLY. The previous name must not appear in code, UI, docs or config (only the historic repo URL and the changelog note)."""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", "data", "data-beta", ".pytest_cache", "screenshots", "fonts", "icons"}
ALLOWED = {"docs/CHANGELOG.md", "CHANGELOG.md", "tests/test_branding.py", "tests/frontend/e2e.mjs"}   # these mention the old name only to check for it
OLD = re.compile(r"veya", re.I)
REPO_URL = "github.com/mouryadusi/veya-app"


def text_files():
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            p = Path(d) / f
            if p.suffix in {".woff2", ".png", ".jpg", ".zip", ".pyc", ".db", ".txt"} and "requirements" not in f:
                continue
            yield p


def test_no_trace_of_the_old_name():
    bad = []
    for p in text_files():
        rel = p.relative_to(ROOT).as_posix()
        if rel in ALLOWED:
            continue
        try:
            t = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if OLD.search(t.replace(REPO_URL, "")):
            bad.append(rel)
    assert not bad, f"old name found in: {bad}"


def test_manifest_and_shell_use_the_new_name():
    mf = json.loads((ROOT / "frontend/manifest.webmanifest").read_text())
    assert mf["name"] == mf["short_name"] == "OFTLY" and mf["display"] == "standalone"
    html = (ROOT / "frontend/index.html").read_text()
    assert "<title>OFTLY" in html and 'apple-mobile-web-app-title" content="OFTLY"' in html and "apple-touch-icon" in html and "manifest.webmanifest" in html
    for icon in ("apple-touch-icon.png", "icon-192.png", "icon-512.png", "icon-maskable-512.png"):
        assert (ROOT / "frontend/icons" / icon).stat().st_size > 500


def test_api_reports_the_new_name(client):
    assert client.get("/api/health").json()["app"] == "OFTLY"
