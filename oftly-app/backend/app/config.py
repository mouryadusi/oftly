"""Paths and settings. Read from the environment at call time so tests can use temp dirs.

Data layout (one directory per account, so one user's data physically cannot be reached from another's request):
    <data>/accounts.db                 users, sessions, password-reset tokens, audit log
    <data>/users/<uuid>/oftly.db       that user's wardrobe, outfits, preferences
    <data>/users/<uuid>/media/*.jpg    that user's photos
The active user comes from the authenticated session (contextvar set by auth.AuthGuard); with no user, data access raises."""
import contextvars
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_uid: contextvars.ContextVar = contextvars.ContextVar("oftly_uid", default=None)
UID_RE = re.compile(r"^[0-9a-f]{32}$")


class NoUserContext(RuntimeError):
    """Raised when per-user data is requested outside an authenticated request."""


def env(name: str, default=None):
    """Setting OFTLY_<NAME> from the environment."""
    return os.environ.get("OFTLY_" + name, default)


def flag(name: str) -> bool:
    return str(env(name, "")).strip().lower() in ("1", "true", "yes", "on")


def data_dir() -> Path:
    p = Path(env("DATA", ROOT / "data"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def accounts_db_path() -> Path:
    return data_dir() / "accounts.db"


def set_user(uid):
    if uid is not None and not UID_RE.match(uid):
        raise ValueError("bad user id")
    return _uid.set(uid)


def reset_user(token):
    _uid.reset(token)


def current_uid():
    return _uid.get()


def user_dir() -> Path:
    uid = _uid.get()
    if not uid:
        raise NoUserContext("no authenticated user")
    p = data_dir() / "users" / uid
    p.mkdir(parents=True, exist_ok=True)
    return p


def media_dir() -> Path:
    p = user_dir() / "media"
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_path() -> Path:
    return user_dir() / "oftly.db"


def demo_enabled() -> bool:
    """Sample items are OFF unless explicitly enabled (dev/test only). Never part of the normal experience."""
    return flag("ENABLE_DEMO")
