"""HTTP provider for a *local* intelligence service. Loopback only: wardrobe data and photos never leave this computer."""
import ipaddress
import time
from urllib.parse import urlparse

import httpx
from pydantic import ValidationError

from .base import CONTRACT, Adjustment, OutfitView, RankContext, Suggestion

TIMEOUT = 3.0
MAX_BYTES = 1_000_000
MAX_IMAGE = 8_000_000
FAIL_LIMIT, COOLDOWN = 3, 60.0


class UnsafeURL(ValueError):
    pass


def _is_ip(h):
    try:
        ipaddress.ip_address(h)
        return True
    except ValueError:
        return False


def _check(url: str) -> str:
    try:
        u = urlparse(url)
        host, _ = (u.hostname or "").lower(), u.port
    except ValueError:
        raise UnsafeURL(url)
    loopback = host == "localhost" or (_is_ip(host) and ipaddress.ip_address(host).is_loopback)
    if u.scheme != "http" or u.username or u.password or not loopback:
        raise UnsafeURL(url)
    return f"http://{u.netloc}"


class HttpProvider:
    def __init__(self, url: str):
        self.base = _check(url)
        self.name = f"http:{urlparse(self.base).netloc}"
        self._fails, self._until = 0, 0.0

    # circuit breaker: after repeated failures stop calling for a while so the app never waits on a dead service
    def _open(self):
        return time.time() < self._until

    def _fail(self):
        self._fails += 1
        if self._fails >= FAIL_LIMIT:
            self._until, self._fails = time.time() + COOLDOWN, 0

    def _call(self, method, path, **kw):
        if self._open():
            return None
        try:
            r = httpx.request(method, self.base + path, timeout=TIMEOUT, follow_redirects=False, **kw)
            r.raise_for_status()
            if len(r.content) > MAX_BYTES:
                raise ValueError("too large")
            self._fails = 0
            return r.json()
        except Exception:
            self._fail()
            return None

    def status(self):
        j = self._call("GET", "/v1/health")
        return {"provider": self.name, "enabled": True, "reachable": bool(j), "contract": CONTRACT,
                "capabilities": (j or {}).get("capabilities", []) if isinstance((j or {}).get("capabilities", []), list) else [],
                "breaker_open": self._open()}

    def rank_outfits(self, outfits: list[OutfitView], ctx: RankContext) -> list[Adjustment]:
        j = self._call("POST", "/v1/rank_outfits", json={"contract": CONTRACT, "context": ctx.model_dump(), "outfits": [o.model_dump() for o in outfits]})
        if not isinstance(j, dict):
            return []
        ids, out = {o.id for o in outfits}, []
        for a in j.get("adjustments", [])[:len(outfits)] if isinstance(j.get("adjustments"), list) else []:
            try:
                adj = Adjustment.model_validate(a)
            except ValidationError:
                continue                        # out-of-range or malformed entries are dropped, not clamped
            if adj.id in ids:
                out.append(adj)
        return out

    def suggest_attributes(self, image_bytes: bytes, content_type: str) -> list[Suggestion]:
        if len(image_bytes) > MAX_IMAGE or content_type not in ("image/jpeg", "image/png", "image/webp"):
            return []
        j = self._call("POST", "/v1/suggest_attributes", files={"image": ("image", image_bytes, content_type)})
        out = []
        for s in (j or {}).get("suggestions", [])[:20] if isinstance((j or {}).get("suggestions"), list) else []:
            try:
                out.append(Suggestion.model_validate(s))
            except ValidationError:
                pass
        return out
