"""Paths. Read from the environment at call time so tests can use temp dirs."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def data_dir() -> Path:
    p = Path(os.environ.get("VEYA_DATA", ROOT / "data"))
    p.mkdir(parents=True, exist_ok=True)
    return p

def media_dir() -> Path:
    p = data_dir() / "media"
    p.mkdir(parents=True, exist_ok=True)
    return p

def db_path() -> Path:
    return data_dir() / "veya.db"
