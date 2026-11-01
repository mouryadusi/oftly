"""Hardening for a local, unauthenticated, single-user API.

A web page on another site can make your browser talk to http://127.0.0.1:8000, and DNS rebinding can make an
attacker's hostname resolve to it. Without accounts these are the realistic attacks, so:
  * Host header must be loopback (or listed in OFTLY_ALLOWED_HOSTS)   -> blocks DNS rebinding
  * state-changing requests with a foreign Origin are refused           -> blocks cross-site form/fetch writes
  * strict response headers (CSP, nosniff, no framing, no referrer)
Authentication is in auth.py; this file is defence in depth, not a substitute. See docs/SECURITY_REPORT.md."""
from urllib.parse import urlparse

from . import config

from starlette.responses import PlainTextResponse

SAFE = {"GET", "HEAD", "OPTIONS"}
CSP = ("default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; "
       "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
HEADERS = {"Content-Security-Policy": CSP, "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
           "X-Frame-Options": "DENY", "Permissions-Policy": "geolocation=(), microphone=(), payment=(), camera=(self)", "Cross-Origin-Resource-Policy": "same-origin",
           "Cross-Origin-Opener-Policy": "same-origin", "Cache-Control": "no-store"}


def allowed_hosts():
    extra = [h.strip().lower() for h in str(config.env("ALLOWED_HOSTS", "")).split(",") if h.strip()]
    return {"127.0.0.1", "localhost", "[::1]", "::1", "testserver", *extra}


MAX_JSON, MAX_UPLOAD = 1_000_000, 10_000_000


class BodyLimit:
    """Refuses oversized or length-less request bodies before they are read (uploads 10 MB, everything else 1 MB)."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] in ("POST", "PUT", "PATCH", "DELETE"):
            h = {k.decode().lower(): v.decode("latin-1") for k, v in scope["headers"]}
            limit = MAX_UPLOAD if h.get("content-type", "").startswith("multipart/form-data") else MAX_JSON
            cl = h.get("content-length")
            if cl is None and "transfer-encoding" in h:
                return await PlainTextResponse("Length required", status_code=411)(scope, receive, send)
            if cl is not None and (not cl.isdigit() or int(cl) > limit):
                return await PlainTextResponse("Request too large", status_code=413)(scope, receive, send)
        await self.app(scope, receive, send)


class LocalGuard:
    """Pure-ASGI middleware (no buffering)."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        h = {k.decode().lower(): v.decode("latin-1") for k, v in scope["headers"]}
        host = h.get("host", "").lower()
        host = host.rsplit(":", 1)[0] if not host.endswith("]") and ":" in host else host
        if host not in allowed_hosts():
            return await PlainTextResponse("Unrecognised host", status_code=400)(scope, receive, send)
        origin = h.get("origin")
        if scope["method"] not in SAFE and origin and origin != "null":
            o = urlparse(origin)
            if (o.hostname or "").lower() not in allowed_hosts() or (o.netloc.lower() != h.get("host", "").lower()):
                return await PlainTextResponse("Cross-site request refused", status_code=403)(scope, receive, send)
        elif scope["method"] not in SAFE and origin == "null":
            return await PlainTextResponse("Cross-site request refused", status_code=403)(scope, receive, send)

        async def send_secure(msg):
            if msg["type"] == "http.response.start":
                hdrs = [(k, v) for k, v in msg["headers"] if k.decode().lower() not in {x.lower() for x in HEADERS}]
                path = scope.get("path", "")
                if scope.get("scheme") == "https" or h.get("x-forwarded-proto") == "https":
                    hdrs.append((b"strict-transport-security", b"max-age=31536000; includeSubDomains"))
                for k, v in HEADERS.items():
                    if k == "Cache-Control" and (path.startswith("/media/") or path.startswith("/fonts/")):
                        continue            # photos and fonts may be cached by the browser
                    hdrs.append((k.lower().encode(), v.encode()))
                msg = {**msg, "headers": hdrs}
            await send(msg)
        await self.app(scope, receive, send_secure)
