"""Accounts, sessions and request authentication for OFTLY.

Design (see docs/SECURITY_REPORT.md):
  * Passwords: Argon2id (argon2-cffi defaults), never stored or logged in clear; unknown-email logins burn an equal hash to avoid timing leaks.
  * Sessions: 256-bit random token in an HttpOnly cookie (or `Authorization: Bearer` for a future native app); only SHA-256(token) is stored,
    so a database leak does not yield usable sessions. Idle timeout 7 days (sliding), absolute lifetime 30 days, revocable (logout / logout-all /
    password change / reset / delete).
  * CSRF: SameSite=Lax cookie + Origin check (security.py) + double-submit token header on every state-changing /api request.
  * Brute force: sliding-window rate limits per IP and per account plus account lockout. In-memory => single process only (see report).
  * Isolation: the authenticated user id selects that user's own database and media directory (config.py). There is no cross-user query path.
  * Recovery: single-use, 30-minute, hashed reset tokens delivered by a pluggable mailer; responses never reveal whether an email exists."""
import hashlib
import hmac
import json
import logging
import re
import secrets
import shutil
import smtplib
import sqlite3
import threading
import time
import uuid
from collections import defaultdict, deque
from contextlib import contextmanager
from email.message import EmailMessage
from http.cookies import SimpleCookie

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

from . import config, db

log = logging.getLogger("oftly.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])
_ph = PasswordHasher()
DUMMY_HASH = _ph.hash("not-a-real-password-for-timing")
SESSION_COOKIE, CSRF_COOKIE, CSRF_HEADER = "oftly_session", "oftly_csrf", "x-csrf-token"
IDLE_TTL, ABS_TTL, RESET_TTL, TOUCH_EVERY = 7 * 86400, 30 * 86400, 30 * 60, 300
SAFE = {"GET", "HEAD", "OPTIONS"}
PRE_SESSION = {"/api/auth/login", "/api/auth/register", "/api/auth/forgot", "/api/auth/reset"}   # no session yet, so no CSRF token yet
COMMON = set("""password password1 password123 123456789012 qwertyuiop12 iloveyou1234 welcome12345 letmein12345 admin1234567 changeme1234
passw0rd12345 1234567890123 abcdefghijkl qwertyuiopas oftly1234567 wardrobe1234 fashion12345 monkey123456 dragon123456 football1234""".split())


# ---------------------------------------------------------------- accounts store
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, pw_hash TEXT NOT NULL, display_name TEXT DEFAULT '',
  created_at REAL NOT NULL, failed_count INTEGER DEFAULT 0, locked_until REAL DEFAULT 0, last_login REAL);
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at REAL NOT NULL, last_seen REAL NOT NULL, expires_at REAL NOT NULL, ua TEXT DEFAULT '');
CREATE INDEX IF NOT EXISTS idx_sess_user ON sessions(user_id);
CREATE TABLE IF NOT EXISTS resets(token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, expires_at REAL NOT NULL, used INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, user_id TEXT, event TEXT, ip TEXT);
"""
_init_done: set = set()


@contextmanager
def acct():
    path = config.accounts_db_path()
    c = sqlite3.connect(path, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    if str(path) not in _init_done:
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript(SCHEMA)
        _init_done.add(str(path))
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


def _h(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def audit(event: str, user_id=None, ip=""):
    try:
        with acct() as c:
            c.execute("INSERT INTO audit(ts,user_id,event,ip) VALUES(?,?,?,?)", (time.time(), user_id, event, (ip or "")[:45]))
    except Exception:       # auditing must never break a request
        log.exception("audit write failed")


# ---------------------------------------------------------------- rate limiting (in-memory, single process)
class Limiter:
    def __init__(self):
        self.hits, self.lock = defaultdict(deque), threading.Lock()

    def check(self, key: str, limit: int, window: float) -> int:
        """Record a hit. Returns 0 if allowed, else seconds until the window frees up."""
        now = time.time()
        with self.lock:
            q = self.hits[key]
            while q and q[0] <= now - window:
                q.popleft()
            if len(q) >= limit:
                return max(1, int(q[0] + window - now) + 1)
            q.append(now)
            return 0

    def clear(self):
        with self.lock:
            self.hits.clear()


limiter = Limiter()


def throttle(key: str, limit: int, window: float):
    wait = limiter.check(key, limit, window)
    if wait:
        raise HTTPException(429, f"Too many attempts. Try again in {wait} seconds.", headers={"Retry-After": str(wait)})


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------- passwords, email
EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$")


def norm_email(e: str) -> str:
    e = (e or "").strip().lower()
    if len(e) > 254 or not EMAIL_RE.match(e):
        raise HTTPException(422, "Enter a valid email address.")
    return e


def password_problem(pw: str, email: str = ""):
    if len(pw) < 12:
        return "Use at least 12 characters. A few random words make a strong, memorable password."
    if len(pw) > 128:
        return "Use at most 128 characters."
    if pw.lower() in COMMON or len(set(pw)) < 5:
        return "That password is too easy to guess. Choose something less common."
    local = email.split("@")[0]
    if local and len(local) >= 4 and local in pw.lower():
        return "Your password shouldn't contain your email name."
    return None


def verify(pw_hash: str, pw: str) -> bool:
    try:
        return _ph.verify(pw_hash, pw)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# ---------------------------------------------------------------- mail (pluggable; nothing is faked)
OUTBOX: list = []        # used only when OFTLY_MAIL=memory (tests)


def send_mail(to: str, subject: str, body: str) -> bool:
    mode = str(config.env("MAIL", "none")).lower()
    if mode == "memory":
        OUTBOX.append({"to": to, "subject": subject, "body": body})
        return True
    if mode == "console":
        log.warning("DEV MAIL to=%s subject=%s\n%s", to, subject, body)       # dev only: prints the reset link to the server log
        return True
    if mode == "smtp":
        try:
            m = EmailMessage()
            m["From"], m["To"], m["Subject"] = config.env("SMTP_FROM"), to, subject
            m.set_content(body)
            with smtplib.SMTP(config.env("SMTP_HOST"), int(config.env("SMTP_PORT", 587)), timeout=10) as s:
                s.starttls()
                if config.env("SMTP_USER"):
                    s.login(config.env("SMTP_USER"), config.env("SMTP_PASS", ""))
                s.send_message(m)
            return True
        except Exception:
            log.exception("SMTP delivery failed")
            return False
    log.warning("Password reset requested but OFTLY_MAIL is not configured; nothing was sent.")
    return False


# ---------------------------------------------------------------- sessions
def _secure_cookie(request: Request) -> bool:
    return config.flag("COOKIE_SECURE") or request.url.scheme == "https"


def create_session(user_id: str, ua: str = "") -> str:
    token, now = secrets.token_urlsafe(32), time.time()
    with acct() as c:
        c.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?)", (_h(token), user_id, now, now, now + ABS_TTL, ua[:120]))
        c.execute("DELETE FROM sessions WHERE expires_at<?", (now,))            # opportunistic cleanup
    return token


def set_cookies(response: Response, request: Request, token: str):
    sec = _secure_cookie(request)
    response.set_cookie(SESSION_COOKIE, token, max_age=ABS_TTL, httponly=True, secure=sec, samesite="lax", path="/")
    response.set_cookie(CSRF_COOKIE, secrets.token_urlsafe(24), max_age=ABS_TTL, httponly=False, secure=sec, samesite="lax", path="/")


def clear_cookies(response: Response):
    for n in (SESSION_COOKIE, CSRF_COOKIE):
        response.delete_cookie(n, path="/")


def resolve_session(token: str):
    """Return the user row for a live session token, enforcing idle + absolute expiry. None if invalid."""
    if not token or len(token) > 200:
        return None
    now = time.time()
    with acct() as c:
        s = c.execute("SELECT * FROM sessions WHERE token_hash=?", (_h(token),)).fetchone()
        if not s or s["expires_at"] < now or s["last_seen"] < now - IDLE_TTL:
            if s:
                c.execute("DELETE FROM sessions WHERE token_hash=?", (s["token_hash"],))
            return None
        if now - s["last_seen"] > TOUCH_EVERY:
            c.execute("UPDATE sessions SET last_seen=? WHERE token_hash=?", (now, s["token_hash"]))
        return c.execute("SELECT id,email,display_name FROM users WHERE id=?", (s["user_id"],)).fetchone()


def revoke(user_id: str, keep_token: str = None):
    with acct() as c:
        if keep_token:
            c.execute("DELETE FROM sessions WHERE user_id=? AND token_hash!=?", (user_id, _h(keep_token)))
        else:
            c.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))


def _token_from_scope(headers: dict):
    ck = SimpleCookie()
    try:
        ck.load(headers.get("cookie", ""))
    except Exception:
        ck = SimpleCookie()
    if SESSION_COOKIE in ck:
        return ck[SESSION_COOKIE].value, ck[CSRF_COOKIE].value if CSRF_COOKIE in ck else None, True
    a = headers.get("authorization", "")
    if a.lower().startswith("bearer "):
        return a[7:].strip(), None, False
    return None, ck[CSRF_COOKIE].value if CSRF_COOKIE in ck else None, True


class AuthGuard:
    """Pure-ASGI middleware: authenticates /api and /media, enforces CSRF, and binds the user's data directory to the request."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path, method = scope["path"], scope["method"]
        protected = (path.startswith("/api/") and path not in ("/api/health", "/api/config", "/api/engine") and not path.startswith("/api/auth/")) or path.startswith("/media/")
        if not (path.startswith("/api/") or path.startswith("/media/")):
            return await self.app(scope, receive, send)           # static frontend files are public (they contain no user data)
        h = {k.decode().lower(): v.decode("latin-1") for k, v in scope["headers"]}
        token, csrf_cookie, via_cookie = _token_from_scope(h)
        user = resolve_session(token) if token else None
        if protected and not user:
            return await JSONResponse({"detail": "Please sign in."}, status_code=401, headers={"Cache-Control": "no-store"})(scope, receive, send)
        if user:
            scope["oftly_user"], scope["oftly_token"] = dict(user), token
        # CSRF double-submit for cookie-authenticated, state-changing calls (bearer tokens are not auto-sent by browsers, so exempt)
        if method not in SAFE and path.startswith("/api/") and path not in PRE_SESSION and via_cookie and user:
            sent = h.get(CSRF_HEADER, "")
            if not csrf_cookie or not sent or not hmac.compare_digest(sent, csrf_cookie):
                return await JSONResponse({"detail": "Security check failed. Reload the page and try again."}, status_code=403)(scope, receive, send)
        tok = config.set_user(user["id"]) if user else None
        try:
            await self.app(scope, receive, send)
        finally:
            if tok is not None:
                config.reset_user(tok)


# ---------------------------------------------------------------- schemas
class Creds(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


class Register(Creds):
    display_name: str = Field("", max_length=60)
    invite: str = Field("", max_length=100)


class Forgot(BaseModel):
    email: str = Field(max_length=254)


class Reset(BaseModel):
    token: str = Field(max_length=200)
    password: str = Field(max_length=256)


class ChangePw(BaseModel):
    current: str = Field(max_length=256)
    new: str = Field(max_length=256)


class PwOnly(BaseModel):
    password: str = Field(max_length=256)


def need_user(request: Request) -> dict:
    u = request.scope.get("oftly_user")
    if not u:
        raise HTTPException(401, "Please sign in.")
    return u


def public_user(u) -> dict:
    return {"id": u["id"], "email": u["email"], "display_name": u["display_name"] or ""}


def invite_ok(code: str) -> bool:
    allowed = [x.strip() for x in str(config.env("INVITE_CODES", "")).split(",") if x.strip()]
    return not allowed or any(hmac.compare_digest(code.strip(), a) for a in allowed)


# ---------------------------------------------------------------- endpoints
@router.post("/register", status_code=201)
def register(body: Register, request: Request, response: Response):
    ip = client_ip(request)
    throttle(f"reg:ip:{ip}", 10, 3600)
    if not invite_ok(body.invite):
        audit("register_bad_invite", None, ip)
        raise HTTPException(403, "A valid invite code is required during the private beta.")
    email = norm_email(body.email)
    problem = password_problem(body.password, email)
    if problem:
        raise HTTPException(422, problem)
    uid, name = uuid.uuid4().hex, body.display_name.strip()
    try:
        with acct() as c:
            c.execute("INSERT INTO users(id,email,pw_hash,display_name,created_at) VALUES(?,?,?,?,?)", (uid, email, _ph.hash(body.password), name, time.time()))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "An account with that email already exists. Try signing in.")
    tok = config.set_user(uid)
    try:
        db.init_db()                       # creates this user's private database and media folder
        if name:
            with db.conn() as c:
                c.execute("INSERT OR REPLACE INTO preferences(key,value) VALUES('preferred_name',?)", (json.dumps(name),))
    finally:
        config.reset_user(tok)
    token = create_session(uid, request.headers.get("user-agent", ""))
    set_cookies(response, request, token)
    audit("register", uid, ip)
    return {"id": uid, "email": email, "display_name": name}


@router.post("/login")
def login(body: Creds, request: Request, response: Response):
    ip, now = client_ip(request), time.time()
    throttle(f"login:ip:{ip}", 30, 600)
    try:
        email = norm_email(body.email)
    except HTTPException:
        verify(DUMMY_HASH, body.password)
        raise HTTPException(401, "Email or password is incorrect.")
    throttle(f"login:acct:{email}", 8, 900)
    with acct() as c:
        u = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    locked = bool(u and u["locked_until"] > now)
    ok = verify(u["pw_hash"] if u else DUMMY_HASH, body.password) and bool(u) and not locked      # always hash, even when locked/unknown
    if not ok:
        if u:
            fails = u["failed_count"] + 1
            with acct() as c:
                c.execute("UPDATE users SET failed_count=?, locked_until=? WHERE id=?", (fails, now + 900 if fails >= 8 else u["locked_until"], u["id"]))
        audit("login_failed", u["id"] if u else None, ip)
        if locked:
            raise HTTPException(429, "Too many failed attempts. Try again in a few minutes, or reset your password.", headers={"Retry-After": "900"})
        raise HTTPException(401, "Email or password is incorrect.")
    with acct() as c:
        c.execute("UPDATE users SET failed_count=0, locked_until=0, last_login=? WHERE id=?", (now, u["id"]))
        if _ph.check_needs_rehash(u["pw_hash"]):
            c.execute("UPDATE users SET pw_hash=? WHERE id=?", (_ph.hash(body.password), u["id"]))
    token = create_session(u["id"], request.headers.get("user-agent", ""))
    set_cookies(response, request, token)
    audit("login", u["id"], ip)
    return {"id": u["id"], "email": u["email"], "display_name": u["display_name"] or ""}


@router.get("/me")
def me(request: Request):
    return public_user(need_user(request))


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response):
    u = need_user(request)
    with acct() as c:
        c.execute("DELETE FROM sessions WHERE token_hash=?", (_h(request.scope["oftly_token"]),))
    clear_cookies(response)
    audit("logout", u["id"], client_ip(request))


@router.post("/logout-all", status_code=204)
def logout_all(request: Request, response: Response):
    u = need_user(request)
    revoke(u["id"])
    clear_cookies(response)
    audit("logout_all", u["id"], client_ip(request))


@router.post("/password", status_code=204)
def change_password(body: ChangePw, request: Request):
    u = need_user(request)
    throttle(f"pw:{u['id']}", 5, 900)
    with acct() as c:
        row = c.execute("SELECT pw_hash FROM users WHERE id=?", (u["id"],)).fetchone()
    if not verify(row["pw_hash"], body.current):
        raise HTTPException(403, "Current password is incorrect.")
    problem = password_problem(body.new, u["email"])
    if problem:
        raise HTTPException(422, problem)
    with acct() as c:
        c.execute("UPDATE users SET pw_hash=? WHERE id=?", (_ph.hash(body.new), u["id"]))
    revoke(u["id"], keep_token=request.scope["oftly_token"])           # every other device is signed out
    audit("password_change", u["id"], client_ip(request))


def make_reset_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    with acct() as c:
        c.execute("DELETE FROM resets WHERE user_id=?", (user_id,))      # only the newest link works
        c.execute("INSERT INTO resets VALUES(?,?,?,0)", (_h(token), user_id, time.time() + RESET_TTL))
    return token


@router.post("/forgot", status_code=202)
def forgot(body: Forgot, request: Request):
    ip = client_ip(request)
    throttle(f"forgot:ip:{ip}", 10, 3600)
    generic = {"detail": "If that email has an account, a reset link is on its way. The link works for 30 minutes."}
    try:
        email = norm_email(body.email)
    except HTTPException:
        return generic
    throttle(f"forgot:acct:{email}", 3, 3600)
    with acct() as c:
        u = c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if u:
        token = make_reset_token(u["id"])
        base = str(config.env("PUBLIC_URL", "")).rstrip("/")
        send_mail(email, "Reset your OFTLY password", f"Open this link to choose a new password (valid 30 minutes, works once):\n\n{base}/#/reset?token={token}\n\nIf you didn't ask for this, ignore this email.")
        audit("reset_requested", u["id"], ip)
    return generic


@router.post("/reset", status_code=204)
def reset(body: Reset, request: Request):
    ip = client_ip(request)
    throttle(f"reset:ip:{ip}", 10, 3600)
    now = time.time()
    with acct() as c:
        r = c.execute("SELECT r.*, u.email FROM resets r JOIN users u ON u.id=r.user_id WHERE token_hash=?", (_h(body.token),)).fetchone()
    if not r or r["used"] or r["expires_at"] < now:
        raise HTTPException(400, "This reset link is invalid or has expired. Request a new one.")
    problem = password_problem(body.password, r["email"])
    if problem:
        raise HTTPException(422, problem)
    with acct() as c:
        c.execute("UPDATE users SET pw_hash=?, failed_count=0, locked_until=0 WHERE id=?", (_ph.hash(body.password), r["user_id"]))
        c.execute("UPDATE resets SET used=1 WHERE token_hash=?", (_h(body.token),))
    revoke(r["user_id"])
    audit("password_reset", r["user_id"], ip)


@router.delete("/account", status_code=204)
def delete_account(body: PwOnly, request: Request, response: Response):
    u = need_user(request)
    throttle(f"del:{u['id']}", 5, 900)
    with acct() as c:
        row = c.execute("SELECT pw_hash FROM users WHERE id=?", (u["id"],)).fetchone()
    if not verify(row["pw_hash"], body.password):
        raise HTTPException(403, "Password is incorrect.")
    with acct() as c:
        c.execute("DELETE FROM users WHERE id=?", (u["id"],))          # cascades to sessions and reset tokens
    shutil.rmtree(config.data_dir() / "users" / u["id"], ignore_errors=True)    # wardrobe, outfits, preferences and every photo
    clear_cookies(response)
    audit("account_deleted", None, client_ip(request))                  # the id is deliberately not kept


@router.get("/config")
def public_config():
    return {"demo_enabled": config.demo_enabled(), "invite_required": bool(str(config.env("INVITE_CODES", "")).strip()),
            "recovery_available": str(config.env("MAIL", "none")).lower() != "none"}
